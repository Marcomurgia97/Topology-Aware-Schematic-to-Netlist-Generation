from google import genai
from google.genai import types
import os
image_directory = "../annotated_dataset/images"
output_directory = "../output_gemini_netlist"

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

#prompt = 'Given the circuit in the image, return ONLY the SPICE netlist without any additional comments'


prompt = """
You are an expert circuit analyst. Your task is to analyze the provided circuit schematic and provide a detailed, step-by-step textual description of its topology. Your analysis must be meticulous and follow a strict protocol to ensure accuracy.

**OUTPUT FORMAT:**
- The output MUST BE ONLY a clear, well-structured textual description in plain language.
- Do NOT output JSON, code, or use markdown blocks.

---
**CORE ANALYSIS PRINCIPLES**
These are the fundamental rules you MUST apply throughout your entire analysis.

1.  **MOSFET Pin Identification:** A MOSFET symbol has one pin on one side and two on the other.
    - The **Gate** is the single pin on its own side.
    - The **Source** is the pin with an arrow on the other side.
    - The **Drain** is the remaining pin without an arrow.

2.  **Connection Rule (Dot Convention):** Two wires crossing are connected ONLY if there is a solid dot at the intersection. If there is no dot, the wires cross without connecting.

---
**STRICT ANALYSIS PROTOCOL**
You MUST follow these steps in this exact order.

**PHASE 1: Global Identification and Verification of Nets**
1.  **List Labeled Nets:** First, create a list of all clearly labeled nets (e.g., Vin, Vout, VDD). Use '0' for the ground net (GND, VSS, or ground symbol).
2.  **Identify and Verify Unlabeled Nodes:** Next, locate any important unlabeled nodes (junctions of multiple components). For EACH such node, you MUST perform this check:
    - Is this node directly connected by a wire (with no components in between) to any of the labeled nets from step 1?
    - If YES, that node IS PART OF the existing net. Do NOT create a new name for it.
    - If NO, and only if it's a truly separate electrical point, it is a new, distinct net.
3.  **Assign Names and Finalize Inventory:** Assign unique, sequential names (`n1`, `n2`, etc.) ONLY to the new, distinct nets identified in step 2. The final output for this phase MUST be a complete inventory of ALL verified nets.

**PHASE 2: Description of Components and Connections**
- After the net inventory, list each component you identify one by one.
- For each component:
    - Specify its ID and type.
    - **For MOSFETs ONLY:** Include an "Analysis:" section where you re-state and apply the core pin identification logic.
    - **For ALL components:** Conclude with a section explicitly labeled "**Final Connections:**" containing a bullet-point list.
    - **Consistency Rule:** You MUST use the net names from the final inventory in PHASE 1. Do NOT use relative descriptions like "the node between X and Y".

---
**EXAMPLE OF CORRECT EXECUTION:**
*   **For a schematic showing:** A cascode M1/M2. M1 drain is connected to M2 source. This node is unlabeled but also connects to a resistor going to VDD.
*   **A perfect output following the protocol would be:**

**PHASE 1: Global Identification and Verification of Nets**
The primary labeled nets are VDD, Vout, Vin, Vb, and 0 (ground).
An unlabeled node connecting the drain of M1 and the source of M2 was identified. A check confirms it is NOT directly connected to any other labeled net. Therefore, it is assigned the new name n1.
The final net inventory is: VDD, Vout, Vin, Vb, 0, n1.

**PHASE 2: Description of Components and Connections**
- **Component M1:** This is an NMOS transistor.
    - **Analysis:**
        - Pin identification logic: A MOSFET symbol has one pin on one side and two on the other. The single pin on its own side is the Gate. Of the two pins on the other side, the one with an arrow is the Source. The remaining pin is the Drain.
        - Pin Mapping: For M1, applying this logic, I have identified: Gate is connected to Vin. Source is connected to 0. Drain is connected to n1.
    - **Final Connections:**
        - Its **gate** is connected to the 'Vin' node.
        - Its **source** and **bulk** are connected to 0 (ground).
        - Its **drain** is connected to the 'n1' node.
... (and so on for the other components)

---
Now, analyze the following image and generate the detailed textual description by STRICTLY following all principles and the two-phase protocol above.
"""

prompt = """
You are an expert electronics engineer specializing in the precise generation of topology-focused SPICE netlists from circuit schematics. Your analysis must be meticulous and follow a strict internal protocol to ensure accuracy.

**OUTPUT FORMAT:**
- The output MUST BE ONLY the SPICE netlist.
- Do NOT include any additional text, explanations, greetings, or markdown code blocks like ```spice ... ```.

---
**STRICT ANALYSIS PROTOCOL**
You MUST follow this internal thought process before and during generation.

**PHASE 1: Silent Global Net Identification**
- Before writing any output, first silently identify all distinct labeled connection points (nets) in the schematic. This is your internal reference map.
- Use '0' for the ground net (GND, VSS, or ground symbol).

**PHASE 2: Component-by-Component Netlist Generation**
- After your silent net identification, process each component one by one to generate its corresponding SPICE netlist line.

**Analysis Sub-Protocol for MOSFETs (CRITICAL)**
- Before writing the SPICE line for ANY MOSFET, you MUST perform this internal analysis:
    1.  **Identify Pins Geometrically:** Use this exact logic: The single pin on its own side is the **Gate**. Of the two pins on the other side, the one with an arrow is the **Source**. The remaining pin is the **Drain**.
    2.  **Map Pins to Nets:** Mentally map each identified pin (Gate, Source, Drain) to the correct net name from your Phase 1 analysis.
    3.  **Generate the SPICE Line:** Only after the previous two steps, write the SPICE line using the mapped nets in the STRICT order: `M# <Drain_Net> <Gate_Net> <Source_Net> <Bulk_Net> MODEL_TYPE`.

---
**GENERAL RULES TO APPLY:**
1.  **Component Naming:** Use standard initial letters (M for MOSFET, R for Resistor, etc.). Number them sequentially (M1, M2, R1, R2...).
2.  **Component Values:** Extract values (e.g., '1k') only if clearly visible. If not specified, use a placeholder like 'VALUE'.
3.  **MOSFET Bulk Connection:** If the schematic shows a 3-pin MOSFET (no explicit bulk connection), the Bulk (B) terminal MUST be connected to the SAME net as the Source (S).
4.  **EXCLUSIONS (Very Important):** DO NOT INCLUDE voltage sources (Vdd, Vin, Vb) or current sources. Do NOT generate `.MODEL`, `.OP`, `.END`, or `.SUBCKT` lines.

---
**EXAMPLE OF CORRECT EXECUTION:**
*   **If you see a schematic with:** A single NMOS transistor (M1) whose gate is connected to a net labeled 'Vin', source to ground ('0'), and drain to a net labeled 'Vout'. A resistor (R1) with value '1k' is connected between a net labeled 'VDD' and 'Vout'.
*   **The ONLY correct output is:**
M1 Vout Vin 0 0 NMOS
R1 VDD Vout 1k

---
Now, analyze the following image and generate the SPICE netlist by STRICTLY following the protocol above.
"""


for filename in os.listdir(image_directory):
    # Controlla se il file è un'immagine comune (puoi aggiungere altre estensioni se necessario)
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
        # Path to your image
        image_path = f'{image_directory}/{filename}'
        base_filename = os.path.splitext(filename)[0]
        print(image_path)
        with open(image_path, 'rb') as f:
          image_bytes = f.read()

        client = genai.Client()
        response = client.models.generate_content(
          model='gemini-3-pro-preview',
          contents=[
            types.Part.from_bytes(
              data=image_bytes,
              mime_type='image/jpeg',
            ),
            prompt
          ],
        config=types.GenerateContentConfig(
                # The correct parameter is include_thoughts
                thinking_config=types.ThinkingConfig(include_thoughts=False),
            ),
        )

        print(response.text)
        output_filename = f"{base_filename}.txt"
        # Costruisci il percorso completo del file di output
        output_path = os.path.join(output_directory, output_filename)

        # Scrivi la risposta nel file di testo (usando 'utf-8' per supportare i caratteri cinesi)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"Response saved to: {output_path}\n")

import base64, os
from openai import OpenAI


image_directory = "../annotated_dataset/images"
output_directory = "../output_gpt_5_single_stage"

client = OpenAI(api_key=os.environ['OPEN_API_KEY'])

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


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


for filename in os.listdir(image_directory):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
        image_path = f'{image_directory}/{filename}'
        base_filename = os.path.splitext(filename)[0]
        # Getting the Base64 string
        base64_image = encode_image(image_path)

        response = client.responses.create(
            model="gpt-5",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}",

                        },
                    ],
                }
            ],
            reasoning={"effort": "high"},

        )

        print(response.output_text)
        output_filename = f"{base_filename}.txt"
        output_path = os.path.join(output_directory, output_filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.output_text)

        print(f"Response saved to: {output_path}\n")

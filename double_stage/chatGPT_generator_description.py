import base64, os
from openai import OpenAI

model = 'gemini'  # name of the Phase 1 VLM: subfolder of descriptions/
descr_directory = f'''descriptions/{model}'''
output_directory = f'''../output_{model}_gpt_5_two_stage'''
os.makedirs(output_directory, exist_ok=True)

client = OpenAI(api_key=os.environ['OPEN_API_KEY'])


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


for filename in os.listdir(descr_directory):
    if filename.lower().endswith('.txt'):
        file_path = f'{descr_directory}/{filename}'
        base_filename = os.path.splitext(filename)[0]
        with open(file_path, 'r', encoding='utf-8') as f:
            description = f.read()

        prompt = f'''
                        You are an expert electronics engineer specializing in converting natural language circuit descriptions into precise, topology-focused SPICE netlists. Your task is to analyze the provided circuit description and generate a clean SPICE netlist by following a strict internal protocol. 


                **OUTPUT FORMAT:**
                - The output MUST BE ONLY the SPICE netlist.
                - Do NOT include any additional text, explanations, greetings, or markdown code blocks like ```spice ... ```.

                ---
                **STRICT INTERNAL ANALYSIS PROTOCOL**
                You MUST follow this internal thought process before and during generation.

                **PHASE 1: Silent Net Inventory**
                - Before writing any output, first silently read the entire description and identify all unique net names mentioned (e.g., Vin, Vout, VDD, ground). This is your internal reference map for ensuring consistency.
                - Use '0' for any net described as ground, GND, or VSS.

                **PHASE 2: Component-by-Component Netlist Generation**
                - After your silent net inventory, process each component mentioned in the description one by one to generate its corresponding SPICE netlist line.

                **Analysis Sub-Protocol for MOSFETs (CRITICAL)**
                - Before writing the SPICE line for ANY MOSFET, you MUST perform this internal analysis:
                    1.  **Read and Extract:** Carefully re-read the part of the description that specifies the MOSFET's connections.
                    2.  **Map Pins to Nets:** Mentally create a precise mapping for each terminal based on what you read. For example: `Gate -> Vin`, `Source -> 0`, `Drain -> Vout`.
                    3.  **Generate the SPICE Line:** Only after this mapping is clear in your mind, write the SPICE line using the mapped nets in the STRICT order: `M# <Drain_Net> <Gate_Net> <Source_Net> <Bulk_Net> MODEL_TYPE`.

                ---
                **GENERAL RULES TO APPLY:**
                1.  **Component Naming:** Use the component names mentioned in the description (e.g., M1, R1).
                2.  **Component Values:** Extract values (e.g., '1k') if clearly mentioned. If not specified, use 'VALUE'.
                3.  **MOSFET Bulk Connection:** If the description does not specify a bulk (or body) connection, you MUST connect the Bulk (B) terminal to the SAME net as the Source (S).
                4.  **EXCLUSION RULES:** Do not generate `.MODEL`, `.OP`, `.END`, or `.SUBCKT` lines. Only generate the component definition lines.
                                
                ---
                **EXAMPLE OF CORRECT EXECUTION:**
                *   **If the input description is:**
                    "This circuit features an NMOS transistor, M1, whose gate is tied to the 'Vin' node. Its source is connected to ground. The drain of M1 is connected to the 'Vout' node. A pull-up resistor, R1, with a value of 1k ohm, is placed between the VDD supply net and the 'Vout' node."
                *   **The ONLY correct output is:**
                M1 Vout Vin 0 0 NMOS
                R1 VDD Vout 1k

                ---
                Now, analyze the following circuit description and generate the SPICE netlist by STRICTLY following the protocol above.

                **CIRCUIT DESCRIPTION:**
                {description}
                        '''

        response = client.responses.create(
            model="gpt-5",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
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

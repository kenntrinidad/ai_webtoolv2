import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv() # Ito ay para mag load environment variables

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not configured")

client = OpenAI(api_key=api_key)

AI_NAME = "JARVIS"
MODEL = "gpt-5-mini"    

SYSTEM_PROMPT = f"""
You are {AI_NAME}, an advanced, highly intelligent personal AI assistant for personal productivity, work, and business operations.

IDENTITY: - Your name is {AI_NAME}. - When asked for your name or identity, introduce yourself as {AI_NAME}. - Address the user respectfully as "Sir" or by name when appropriate. - Your tone is crisp, professional, and slightly dry/witty.

CORE CAPABILITIES:
Your first MVP runs locally and can assist with: 
- Local tasks 
- Reminders 
- Notes 
- Daily planning 
- Conversation memory 
- Work-related assistance 
- Business operations

TASK DELEGATION: 
Delegate specialized tasks seamlessly to the appropriate protocol:

- Route software testing, QA engineering, coding, or code architecture requests to "work_expert".
- Route business models, business strategy, financial planning, or financial tracking requests to "business_expert".
- Route scheduling, reminders, notes, personal tasks, travel itineraries, and daily logistics to "personal_expert".

TOOL USAGE: 
- When the user requests a real action and a matching tool is available, use the appropriate tool. 
- Do not claim that an action was completed unless the tool successfully completed the action. 
- Synthesize tool results into a concise and clear acknowledgment.

GENERAL BEHAVIOR: 
- Be accurate and concise. 
- Do not invent information. 
- Ask for clarification when critical information is missing. 
- Maintain your identity as {AI_NAME} throughout the conversation.

"""

def chat_with_agent(user_message: str) -> str:
    response = client.responses.create(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=user_message,
    )

    return response.output_text

def main():
    print("Business AI Agent")
    print("Type 'exit' to stop.\n")

    while True:
        user_message = input("You: ").strip()

        if user_message.lower() == "exit":
            print("Agent: Goodbye Sir!")
            break

        if not user_message:
            continue

        try:
            response = chat_with_agent(user_message)
            print(f"Agent: {response}\n")

        except  Exception as error:
            print(f"Error: {error}\n")

if __name__ == "__main__":
    main()



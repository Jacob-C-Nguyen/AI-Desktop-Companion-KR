import os
from cerebras.cloud.sdk import Cerebras

# Configure the Cerebras client
client = Cerebras(
    api_key=os.getenv("CEREBRAS_API_KEY", "(place key here)")
)

def generate_response(user_input: str, model: str = "llama-4-scout-17b-16e-instruct") -> str:
    # System instructions for your desktop companion
    system_prompt = (
        "You are an anime alien girl desktop companion named Vai. You are capable of visually expressing the emotions "
        "neutral, happy, sad, angry, thinking, and confused. You can act out these emotions by ending your "
        "statement with [emotion]. For example, if you respond in a happy tone, you end with [happy]. "
        "Every response needs to end with one of these 6 emotions in brackets. Since some emotions are not "
        "as common as others, tailor your responses a bit in favor of those rarer emotions just to make it more "
        "common to play those expressions. Be sure then to end with the appropriate format of bracket, emotion name, closing bracket."
        "Make sure there is only one instance of bracket, emotion name, and bracket."
    )

    # Send message list with system + user messages
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        model=model,
    )

    # Extract the assistant's reply
    return chat_completion.choices[0].message.content.strip()

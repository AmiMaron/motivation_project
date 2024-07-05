import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AssistantManager:
    def __init__(self):
        # Initialize OpenAI client
        self.client = OpenAI()
        # Get API key from environment variable
        self.api_key = os.getenv('OPENAI_API_KEY')
        # Set assistant IDs (make sure these are correct and the assistants are properly configured)
        self.chat_assistant_id = "asst_6rJYTCH4aym7lm3h2FeM4Fcc"
        self.moderation_assistant_id = "asst_mmvSEv260sF7lnHwia2bpHtJ"

    def chat_with_user(self, user_input):
        try:
            # Step 1: Use moderation assistant to check for harmful language
            moderation_thread = self.client.beta.threads.create()
            self.client.beta.threads.messages.create(
                thread_id=moderation_thread.id,
                role="user",
                content=f"Check if this message contains harmful language: '{user_input}'. Respond with 'HARMFUL' if it does, or 'SAFE' if it doesn't."
            )
            moderation_run = self.client.beta.threads.runs.create(
                thread_id=moderation_thread.id,
                assistant_id=self.moderation_assistant_id
            )
            
            # Wait for moderation run to complete
            while True:
                moderation_run = self.client.beta.threads.runs.retrieve(
                    thread_id=moderation_thread.id,
                    run_id=moderation_run.id
                )
                if moderation_run.status == "completed":
                    break
                time.sleep(1)
            
            # Get moderation response
            moderation_messages = self.client.beta.threads.messages.list(thread_id=moderation_thread.id)
            moderation_response = moderation_messages.data[0].content[0].text.value
            
            # Check if the message is flagged as harmful
            if "HARMFUL" in moderation_response.upper():
                return "I'm sorry, but I can't respond to that kind of language."
            
            # Step 2: If not harmful, proceed with chat assistant
            chat_thread = self.client.beta.threads.create()
            self.client.beta.threads.messages.create(
                thread_id=chat_thread.id,
                role="user",
                content=user_input
            )
            chat_run = self.client.beta.threads.runs.create(
                thread_id=chat_thread.id,
                assistant_id=self.chat_assistant_id
            )
            
            # Wait for chat run to complete
            while True:
                chat_run = self.client.beta.threads.runs.retrieve(
                    thread_id=chat_thread.id,
                    run_id=chat_run.id
                )
                if chat_run.status == "completed":
                    break
                time.sleep(1)
            
            # Get chat response
            chat_messages = self.client.beta.threads.messages.list(thread_id=chat_thread.id)
            chat_response = chat_messages.data[0].content[0].text.value
            
            return chat_response
        
        except Exception as e:
            return f"An error occurred: {str(e)}"

# Main execution
if __name__ == "__main__":
    assistant_manager = AssistantManager()
    
    print("Chat started. Type 'exit' to end the conversation.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Chat ended. Goodbye!")
            break
        response = assistant_manager.chat_with_user(user_input)
        print(f"Assistant: {response}")
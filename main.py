import openai
import os
from dotenv import load_dotenv
import time
import json
import datetime

load_dotenv()

class AssistantManager:
    def __init__(self):
        # Initialize OpenAI client and assistant IDs
        self.client = openai.Client()
        self.api_key = os.getenv('OPENAI_API_KEY')  # environment variable
        self.main_assistant_id = "asst_VxB5X5MnbE1udKNdgOI2HzbQ"
        
        # prfile builder assistants variables
        self.profile_builder_assistant_id = "asst_mmvSEv260sF7lnHwia2bpHtJ"
        self.thread_summarizer_assistant_id = "asst_et4eUKFzOFGGbQZcZ3NtiVcf"
        self.blank_profile_path = "users/blank_profile.json"
        self.user_profile = None

        # other assistant variables
        self.method_1 = "TO BE IMPLEMENTED"
        self.method_2 = "TO BE IMPLEMENTED"
        self.method_3 = "TO BE IMPLEMENTED"

        self.thread_id = None
        self.conversation_log = []

    def create_thread(self):
        thread = self.client.beta.threads.create()
        self.thread_id = thread.id

    def get_assistant_response(self, run_id, thread_id):
        while True:
            run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if run.completed_at:
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                return messages.data[0].content[0].text.value
            time.sleep(1)

    def add_message_to_thread(self, role, content):
        self.client.beta.threads.messages.create(
            thread_id=self.thread_id, role=role, content=content
        )
        self.conversation_log.append({"role": role, "content": content})

    def run_assistant(self, instructions):
        return self.client.beta.threads.runs.create(
            thread_id=self.thread_id,
            assistant_id=self.main_assistant_id,
            instructions=instructions,
        )

    def thread_summary(self):
        summary_thread = self.client.beta.threads.create()
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_log[:-1]])
        self.client.beta.threads.messages.create(
            thread_id=summary_thread.id,
            role="user",
            content=f"Please provide a short summary of this conversation:\n\n{conversation_text}"
        )
        summary_run = self.client.beta.threads.runs.create(
            thread_id=summary_thread.id,
            assistant_id=self.thread_summarizer_assistant_id,
        )
        return self.get_assistant_response(summary_run.id, summary_thread.id)

    def save_conversation_log(self, user_name, thread_date):
        log_data = {
            "thread_name": f"{user_name}_{thread_date.replace(' ', '_')}",
            "thread_id": self.thread_id,
            "assistant_id": self.main_assistant_id,
            "thread_date": thread_date,
            "thread_summary": self.thread_summary(),
            "conversation": self.conversation_log[:-1]
        }
        log_filename = f"Users/{user_name}/logs/thread_log_{time.strftime('%Y%m%d-%H%M%S')}.json"
        os.makedirs(os.path.dirname(log_filename), exist_ok=True)
        with open(log_filename, 'w') as f:
            json.dump(log_data, f, indent=2)
        print(f"Conversation log saved to {log_filename}")

    def build_user_profile(self, user_name):
        profile_thread = self.client.beta.threads.create()
        
        with open(self.blank_profile_path, 'r') as json_file:
            data = json.load(json_file)

        # Initialize the assistant
        self.client.beta.threads.messages.create(
            thread_id=profile_thread.id,
            role="user",
            content="You are a very friendly assistant (which uses emojis) helping to build a user profile. Ask one question at a time and wait for the user's response before moving to the next question."
        )

        def ask_question(key, value, context=""):
            instruction = f"{context}\n\nPlease ask the user for their {key.replace('_', ' ')}."
            self.client.beta.threads.messages.create(
                thread_id=profile_thread.id,
                role="user",
                content=instruction
            )
            run = self.client.beta.threads.runs.create(
                thread_id=profile_thread.id,
                assistant_id=self.profile_builder_assistant_id
            )
            assistant_question = self.get_assistant_response(run.id, profile_thread.id)
            print(f"MotivateBot: {assistant_question}")
            user_response = input("You: ")
            
            # Send user's response back to the assistant
            self.client.beta.threads.messages.create(
                thread_id=profile_thread.id,
                role="user",
                content=f"User's response for {key}: {user_response}"
            )
            return user_response

        def populate_dict(data, context=""):
            for key, value in data.items():
                if isinstance(value, dict):
                    populate_dict(value, context=f"{context} {key}")
                else:
                    if key != "user_name":
                        data[key] = ask_question(key, value, context=context)

        populate_dict(data)

        data["user_name"] = user_name

        new_user_profile = f"Users/{user_name}/{user_name}_profile.json"
        os.makedirs(os.path.dirname(new_user_profile), exist_ok=True)
        with open(new_user_profile, 'w') as f:
            json.dump(data, f, indent=2)

        self.user_profile = data

        thread_log = self.get_thread_log(profile_thread.id)
        log_file_path = f"Users/{user_name}/{user_name}_conversation_log.txt"
        with open(log_file_path, 'w', encoding='utf-8') as log_file:
            log_file.write(thread_log)

    def get_thread_log(self, thread_id):
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)
        sorted_messages = sorted(messages.data, key=lambda x: x.created_at)
        return "\n\n".join([
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(message.created_at))} - "
            f"{message.role.capitalize()}: {message.content[0].text.value}"
            for message in sorted_messages
        ])

    def load_user_profile(self, user_name):
        profile_path = f"users/{user_name}/{user_name}_profile.json"
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                self.user_profile = json.load(f)
            return True
        return False

def main():
    manager = AssistantManager() # Initialize the assistant manager
    
    # Check if the user has a profile, if not, create one
    user_name = input("Please enter your user name: ")
    if manager.load_user_profile(user_name):
        print(f"Welcome back, {user_name}!")
    else:
        print(f"Welcome, {user_name}! It seems you're new here. Let's create your user profile.")
        manager.build_user_profile(user_name)

    
    manager.create_thread()
    thread_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Chat with the MotivateBot. Type 'quit' to end the conversation.")
    
    while True:
        instructions = "Hold a conversation with the user."
        if manager.user_profile:
            instructions += f" User profile: {json.dumps(manager.user_profile)}"
        run = manager.run_assistant(instructions)
        response = manager.get_assistant_response(run.id, manager.thread_id)
        print(f"MotivateBot: {response}")
        manager.add_message_to_thread("assistant", response)
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            manager.save_conversation_log(user_name, thread_date)
            break
        manager.add_message_to_thread("user", user_input)

if __name__ == "__main__":
    main()
import openai
import os
from dotenv import load_dotenv
import time
import json
import datetime

load_dotenv()

class AssistantManager:
    def __init__(self):
        self.client = openai.Client()
        self.api_key = os.getenv('sk-proj-CVAhe9WUyE9tDqjUHdT6T3BlbkFJP3smh9MbWjHxw4pRobvg')
        self.assistant_id = "asst_VxB5X5MnbE1udKNdgOI2HzbQ"
        self.summary_assistant_id = "asst_et4eUKFzOFGGbQZcZ3NtiVcf"
        self.profile_builder_assistant_id = "asst_rCJvwJ62cMhl47Kgg3QYG856"
        self.thread_id = None
        self.conversation_log = []
        self.user_profile = None

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
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
            instructions=instructions,
        )
        return run

    def thread_summary(self):
        # Generate summary using another OpenAI assistant
        summary_thread = self.client.beta.threads.create()

        conversation_list = self.conversation_log[:-1] # crop the last 'quit' message from the user
        
        # Add the conversation log to the new thread
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_list])
        self.client.beta.threads.messages.create(
            thread_id=summary_thread.id,
            role="user",
            content=f"Please provide a short summary of this conversation:\n\n{conversation_text}"
        )
        
        # Run the summary assistant
        summary_run = self.client.beta.threads.runs.create(
            thread_id=summary_thread.id,
            assistant_id=self.summary_assistant_id,
        )
        
        return self.get_assistant_response(summary_run.id, summary_thread.id)
        
      
    def save_conversation_log(self, user_name, thread_date):        
        log_data = {
            "thread_name": f"{user_name}_{thread_date.replace(' ', '_')}",
            "thread_id": self.thread_id,
            "assistant_id": self.assistant_id,
            "thread_date": thread_date,
            "thread_summary": self.thread_summary(),
            "conversation": self.conversation_log[:-1] # crop the last 'quit' message from the user
        }
        
        log_filename = f"Users/{user_name}/logs/thread_log_{time.strftime('%Y%m%d-%H%M%S')}.json"
        os.makedirs(os.path.dirname(log_filename), exist_ok=True)
        with open(log_filename, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"Conversation log saved to {log_filename}")

    def build_user_profile(self, user_name):
      profile_thread = self.client.beta.threads.create()
      user_data = {
          "user_name": user_name,
          "personal_info": {
              "name": "",
              "date_of_birth": "",
              "gender": "",
              "email": "",
              "phone": "",
              "profession": "",
              "address": {
                  "city": "",
                  "country": ""
              }
          }
      }

      # Function to ask a question and get a response
      def ask_question(question):
          self.client.beta.threads.messages.create(
              thread_id=profile_thread.id,
              role="user",
              content=question
          )
          
          run = self.client.beta.threads.runs.create(
              thread_id=profile_thread.id,
              assistant_id=self.profile_builder_assistant_id
          )

          assistant_response = self.get_assistant_response(run.id, profile_thread.id)
          print(f"MotivateBot: {assistant_response}")
          user_response = input("You: ")
          return user_response

      # Initial instruction for the assistant
      self.client.beta.threads.messages.create(
          thread_id=profile_thread.id,
          role="user",
          content="You are a friendly assistant helping to build a user profile. Ask questions in a natural, conversational way to gather the required information. After each user response, ask the next question."
      )

      # Function to recursively populate the user_data dictionary
      def populate_dict(data):
          for key, value in data.items():
                if isinstance(value, dict):
                    populate_dict(value)
                else:
                  if value == "":
                    data[key] = ask_question(key)

      # Populate the user_data dictionary
      populate_dict(user_data)

      # Save the user profile
      new_user_profile = f"Users/{user_name}/{user_name}_profile.json"
      os.makedirs(os.path.dirname(new_user_profile), exist_ok=True)
      with open(new_user_profile, 'w') as f:
          json.dump(user_data, f, indent=2)

      print(f"User profile for {user_name} has been created and saved.")
      self.user_profile = user_data

    def load_user_profile(self, user_name):
        profile_path = f"users/{user_name}/{user_name}_profile.json"
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                self.user_profile = json.load(f)
            return True
        return False

def main():
    manager = AssistantManager()
    user_name = input("Please enter your user name: ")
   
    if manager.load_user_profile(user_name):
        print(f"Welcome back, {user_name}!")
    else:
        print(f"Welcome, {user_name}! It seems you're new here. Let's create your user profile.")
        manager.build_user_profile(user_name)

    manager.create_thread()
    thread_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Chat with the MotivateBot. Type 'quit' to end the conversation.")
    user_input = ""
    while True:
        if user_input.lower() == 'quit':
            manager.save_conversation_log(user_name, thread_date)
            break
        instructions = "Hold a conversation with the user."
        if manager.user_profile:
            instructions += f" User profile: {json.dumps(manager.user_profile)}"
        run = manager.run_assistant(instructions)
        response = manager.get_assistant_response(run.id, manager.thread_id)
        print(f"MotivateBot: {response}")
        manager.add_message_to_thread("assistant", response)
        user_input = input("You: ")
        manager.add_message_to_thread("user", user_input)

if __name__ == "__main__":
    main()
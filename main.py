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
        self.chat_thread = None
        self.thread_id = None
        self.chat_log = []

    # load user profile
    def load_user_profile(self, user_name):
        profile_path = f"users/{user_name}/{user_name}_profile.json"
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                self.user_profile = json.load(f)
            return True
        return False

    # build user profile
    def build_user_profile(self, user_name):
        try:
            profile_thread = self.client.beta.threads.create()
            
            with open(self.blank_profile_path, 'r') as json_file:
                data = json.load(json_file)

            # Initialize the assistant with the user's name
            self.client.beta.threads.messages.create(
                thread_id=profile_thread.id,
                role="user",
                content=f"You are a very friendly assistant (which uses emojis) helping to build a user profile for {user_name}. Ask one question at a time and wait for the user's response before moving to the next question. Focus only on personal information. Always refer to the user as {user_name}."
            )

            def ask_question(key):
                instruction = f"\n\nPlease ask {user_name} for their {key.replace('_', ' ')}."
                self.client.beta.threads.messages.create(
                    thread_id=profile_thread.id,
                    role="user",
                    content=instruction
                )
                
                run = self.client.beta.threads.runs.create(
                    thread_id=profile_thread.id,
                    assistant_id=self.profile_builder_assistant_id
                )
                
                # Wait for run to complete
                while True:
                    run_status = self.client.beta.threads.runs.retrieve(
                        thread_id=profile_thread.id,
                        run_id=run.id
                    )
                    if run_status.status == "completed":
                        break
                    time.sleep(0.1)
                
                # Get assistant's question
                messages = self.client.beta.threads.messages.list(thread_id=profile_thread.id)
                assistant_question = messages.data[0].content[0].text.value
                
                print(f"MotivateBot: {assistant_question}")
                user_response = input("You: ")
                
                # Send user's response back to the assistant
                self.client.beta.threads.messages.create(
                    thread_id=profile_thread.id,
                    role="user",
                    content=f"{user_name}'s response for {key}: {user_response}"
                )
                return user_response

            def populate_personal_info(personal_info):
                for key, value in personal_info.items():
                    if isinstance(value, dict):
                        populate_personal_info(value)
                    else: 
                        personal_info[key] = ask_question(key)


            # Populate the rest of the personal_info
            populate_personal_info(data["personal_info"])

            # Set other parts of the profile
            data["user_name"] = user_name
            data["status"]["last_updated"] = datetime.datetime.now().isoformat()
            data["status"]["summary"] = "Personal information collected"

            new_user_profile = f"users/{user_name}/{user_name}_profile.json"
            os.makedirs(os.path.dirname(new_user_profile), exist_ok=True)
            with open(new_user_profile, 'w') as f:
                json.dump(data, f, indent=2)

            self.user_profile = data
            
            return "User personal information collected successfully"
        
        except Exception as e:
            return f"An error occurred while building the user profile: {str(e)}"

    # main chat with user
    def chat_with_user(self, user_input):
        try:
            if self.chat_thread is None:
                self.chat_thread = self.client.beta.threads.create()
        
            # Append user input to chat log
            self.chat_log.append({"role": "user", "content": user_input})

            consultance_input = self.get_advice(self.chat_log)

            self.client.beta.threads.messages.create(
                thread_id=self.chat_thread.id,
                role="user",
                content=f"""user_input: {user_input}, consultance input: {consultance_input}"""
            )
            chat_run = self.client.beta.threads.runs.create(
                thread_id=self.chat_thread.id,
                assistant_id=self.main_assistant_id
            )
            
            # FOR DEBUG - REMOVE LATER
            # print the last content of the thread
            messages = self.client.beta.threads.messages.list(thread_id=self.chat_thread.id)
            print(messages.data[-1].content[0].text.value)

            # Wait for chat run to complete
            while True:
                chat_run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.chat_thread.id,
                    run_id=chat_run.id
                )
                if chat_run.status == "completed":
                    break
                time.sleep(0.1)
            
            # Get chat response
            chat_messages = self.client.beta.threads.messages.list(thread_id=self.chat_thread.id)
            chat_response = chat_messages.data[0].content[0].text.value
            
            # Append assistant response to chat log
            self.chat_log.append({"role": "assistant", "content": chat_response})

            return chat_response
        
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            self.chat_log.append({"role": "system", "content": error_message})
            return error_message  
        
    # getting advice from the advisors
    def get_advice(self, chat_log):
        # consultance with methods
        method_chooser = self.client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """You consult to the main motivation bot. Your role is to understand which method is the best to use for the user's needs. You have one of the methods to choose from: 
             'method_1' - Framing tasks in terms of their importance for larger goals (“remember, you want to do well on this test so you can…” [live a good life /be an awesome programmer / become a doctor / …])
             'method_2' - Framing tasks in terms of social connection (“Your mother will be proud of you” “your boss counts on you” “your clients need your help”)
             'method_3' - Making the future present (“In five years, when you look at yourself, do you want to be the person who did this today")
             'None' - No method is currently suitable for the user's needs. 
             Return ONLY one of the following options: 'method_1', 'method_2', 'method_3' or 'None'."""},
            {"role": "user", "content": f"{chat_log}"}
        ]
        )

        # FOR DEBUG - REMOVE LATER
        print("THE CHOICE:", method_chooser.choices[0].message.content)

        def method_1(chat_log):
            method_1 = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are a consultant to the main motivation bot. 
                Your role is to consult based on the following method:
                frame tasks in terms of their importance for larger goals (“remember, you want to do well on this test so you can…” [live a good life /be an awesome programmer / become a doctor / …])
                """},
                {"role": "user", "content": f"{chat_log}"}
            ]
            )
            return method_1.choices[0].message.content
        
        def method_2(chat_log):
            method_2 = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are a consultant to the main motivation bot. 
                Your role is to consult based on the following method: 
                frame tasks in terms of social connection (“Your mother will be proud of you” “your boss counts on you” “your clients need your help”)
                """},
                {"role": "user", "content": f"{chat_log}"}
            ]
            )
            return method_2.choices[0].message.content
        
        def method_3(chat_log):
            method_3 = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are a consultant to the main motivation bot. 
                Your role is to consult based on the following method: 
                make the future present (“In five years, when you look at yourself, do you want to be the person who did this today)
                """},
                {"role": "user", "content": f"{chat_log}"}
            ]
            )
            return method_3.choices[0].message.content
        
        if "method_1" in method_chooser.choices[0].message.content:
            return method_1(chat_log)
        elif "method_2" in method_chooser.choices[0].message.content:
            return method_2(chat_log)
        elif "method_3" in method_chooser.choices[0].message.content:
            return method_3(chat_log)
        else:
            return "None"

    # save chat log
    def save_chat_log(self, user_name, thread_date):
        log_data = {
            "thread_name": f"{user_name}_{thread_date.replace(' ', '_')}",
            "thread_id": self.chat_thread.id,
            "assistant_id": self.main_assistant_id,
            "thread_date": thread_date,
            "chat": self.chat_log
        }
        log_filename = f"Users/{user_name}/logs/thread_log_{time.strftime('%Y%m%d-%H%M%S')}.json"
        os.makedirs(os.path.dirname(log_filename), exist_ok=True)
        with open(log_filename, 'w') as f:
            json.dump(log_data, f, indent=2)
        print(f"chat log saved to {log_filename}")

def main():
    manager = AssistantManager() # Initialize the assistant manager
    # provide instructions to the "manager" assistant

    # Check if the user has a profile, if not, create one
    user_name = input("Please enter your user name: ")
    if manager.load_user_profile(user_name):
        print(f"Welcome back, {user_name}!")
    else:
        print(f"Welcome, {user_name}! It seems you're new here. Let's create your user profile.")
        manager.build_user_profile(user_name)

    
    # manager.create_thread()
    thread_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Chat with the MotivateBot. Type 'exit' to end the chat.")
    
    while True:
        instructions = "Hold a chat with the user."
        # add user profile to instructions
        if manager.user_profile:
            instructions += f" User profile: {json.dumps(manager.user_profile)}"
        
        # chat with user
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Chat ended. Goodbye!")
            manager.save_chat_log(user_name, thread_date)
            break
        else:
            response = manager.chat_with_user(user_input)
            print(f"Assistant: {response}")

if __name__ == "__main__":
    main()
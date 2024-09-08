import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import threading
import pyperclip
import queue
import os
from dotenv import load_dotenv
from fyers_apiv3 import fyersModel
import webbrowser
import requests
import hashlib
import json
from tkinter import ttk

# Load environment variables
load_dotenv()

class LoginWindow:
    def __init__(self, master):
        self.master = master
        master.title("ProCodeOne - Login")
        master.geometry("300x150")
        master.resizable(False, False)

        self.frame = tk.Frame(master)
        self.frame.pack(pady=20)

        self.email_label = tk.Label(self.frame, text="Email:")
        self.email_label.grid(row=0, column=0, sticky="e")
        self.email_entry = tk.Entry(self.frame)
        self.email_entry.grid(row=0, column=1)

        self.password_label = tk.Label(self.frame, text="Password:")
        self.password_label.grid(row=1, column=0, sticky="e")
        self.password_entry = tk.Entry(self.frame, show="*")
        self.password_entry.grid(row=1, column=1)

        self.login_button = tk.Button(self.frame, text="Login", command=self.login)
        self.login_button.grid(row=2, column=1, pady=10)

    def login(self):
        email = self.email_entry.get()
        password = self.password_entry.get()

        # API endpoint
        url = "https://56oflqud0d.execute-api.ap-south-1.amazonaws.com/production/login"

        # Prepare the data for the POST request
        data = {
            "email": email,
            "password": password
        }

        try:
            # Send POST request to the API
            response = requests.post(url, json=data)
            
            # Parse the JSON response
            result = response.json()

            if response.status_code == 200 and result.get('success') == 1:
                messagebox.showinfo("Login Successful", "Welcome to ProCodeOne!")
                self.master.destroy()
                root = tk.Tk()
                app = OptionsWindow(root)
                root.mainloop()
            else:
                messagebox.showerror("Login Failed", result.get('message', "Invalid email or password"))
        except requests.RequestException as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid response from server")

class OptionsWindow:
    def __init__(self, master):
        self.master = master
        master.title("ProCodeOne - Options")
        master.geometry("300x150")
        master.resizable(False, False)

        self.frame = tk.Frame(master)
        self.frame.pack(pady=20)

        self.auth_button = tk.Button(self.frame, text="Authenticate Fyers", command=self.authenticate_fyers)
        self.auth_button.pack(pady=10)

        self.run_script_button = tk.Button(self.frame, text="Run Script", command=self.run_script)
        self.run_script_button.pack(pady=10)

    def authenticate_fyers(self):
        self.master.withdraw()  # Hide the current window
        root = tk.Toplevel(self.master)
        app = FyersAuthWindow(root, self.master)

    def run_script(self):
        self.master.withdraw()  # Hide the current window
        root = tk.Toplevel(self.master)
        app = ScriptRunnerApp(root, self.master)

class FyersAuthWindow:
    def __init__(self, master, parent):
        self.master = master
        self.parent = parent
        master.title("ProCodeOne - Fyers Authentication")
        master.geometry("400x300")
        master.resizable(False, False)

        self.frame = tk.Frame(master)
        self.frame.pack(pady=20)

        self.auth_button = tk.Button(self.frame, text="Start Authentication", command=self.start_auth)
        self.auth_button.pack(pady=10)

        self.status_label = tk.Label(self.frame, text="")
        self.status_label.pack(pady=10)

        self.auth_code_label = tk.Label(self.frame, text="Enter Auth Code:")
        self.auth_code_entry = tk.Entry(self.frame, width=40)
        self.submit_button = tk.Button(self.frame, text="Submit", command=self.submit_auth_code)

        self.back_button = tk.Button(self.frame, text="Back", command=self.go_back)
        self.back_button.pack(side=tk.BOTTOM, pady=10)

        # Fyers-specific attributes
        self.redirect_uri = os.getenv('REDIRECT_URI')
        self.client_id = os.getenv('CLIENT_ID')
        self.secret_key = os.getenv('SECRET_KEY')
        self.pin = os.getenv('PIN')
        self.current_directory = os.getcwd()
        self.log_path = self.current_directory
        self.refresh_token_path = os.path.join(self.current_directory, "refresh_token.txt")
        self.access_token = None
        self.appSession = None

    def generate_token_from_refresh(self, refresh_token):
        url = 'https://api-t1.fyers.in/api/v3/validate-refresh-token'
        headers = {'Content-Type': 'application/json'}
        data = {
            'grant_type': 'refresh_token',
            'appIdHash': hashlib.sha256(f"{self.client_id}:{self.secret_key}".encode()).hexdigest(),
            'refresh_token': refresh_token,
            'pin': self.pin
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            return response.json().get('access_token')
        return None

    def start_auth(self):
        # Try to load existing refresh token
        if os.path.exists(self.refresh_token_path):
            with open(self.refresh_token_path, 'r') as file:
                refresh_token = file.read().strip()
            
            # Try to generate access token using refresh token
            self.access_token = self.generate_token_from_refresh(refresh_token)
            
            if self.access_token:
                self.status_label.config(text="Access token generated using refresh token")
                self.save_tokens()
                return
            else:
                self.status_label.config(text="Failed to generate access token using refresh token. Please enter auth code.")
                self.show_auth_code_input()
        else:
            self.status_label.config(text="Refresh token not found. Please enter auth code.")
            self.show_auth_code_input()

        # If access token is not generated, use the auth code method
        grant_type = "authorization_code"
        response_type = "code"
        state = "sample"
        
        self.appSession = fyersModel.SessionModel(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            response_type=response_type,
            state=state,
            secret_key=self.secret_key,
            grant_type=grant_type
        )

        generateTokenUrl = self.appSession.generate_authcode()
        webbrowser.open(generateTokenUrl, new=1)

    def show_auth_code_input(self):
        self.auth_code_label.pack()
        self.auth_code_entry.pack()
        self.submit_button.pack(pady=10)

    def submit_auth_code(self):
        if not self.appSession:
            self.status_label.config(text="Please start authentication first.")
            return

        auth_code = self.auth_code_entry.get()
        self.appSession.set_token(auth_code)
        response = self.appSession.generate_token()

        try:
            self.access_token = response["access_token"]
            refresh_token = response["refresh_token"]
            self.status_label.config(text="Token generated using auth code")
            
            # Save refresh token for future use
            with open(self.refresh_token_path, 'w') as file:
                file.write(refresh_token)

            self.save_tokens()

        except KeyError as e:
            self.status_label.config(text=f"Error retrieving tokens: {e}")
            print("Response:", response)

    def save_tokens(self):
        # Initialize the FyersModel with the access token
        fyers = fyersModel.FyersModel(token=self.access_token, is_async=False, client_id=self.client_id, log_path=self.log_path)

        # Get details about your account
        response = fyers.get_profile()
        print(response)

        # Save client_id and access_token to text files
        with open(os.path.join(self.current_directory, "client_id.txt"), 'w') as file:
            file.write(self.client_id)

        with open(os.path.join(self.current_directory, "access_token.txt"), 'w') as file:
            file.write(self.access_token)

        self.status_label.config(text="Authentication successful. Tokens saved.")
        self.master.after(2000, self.go_to_script_runner)  # Wait 2 seconds before going to ScriptRunnerApp

    def go_to_script_runner(self):
        self.master.destroy()
        root = tk.Toplevel(self.parent)
        app = ScriptRunnerApp(root, self.parent)

    def go_back(self):
        self.master.destroy()
        self.parent.deiconify()  # Show the parent window

class ScriptRunnerApp:
    def __init__(self, master, parent):
        self.master = master
        self.parent = parent
        master.title("ProCodeOne - TradeBotOne")
        master.geometry("500x450")
        master.resizable(False, False)

        self.script_config = self.load_script_config()

        self.frame = tk.Frame(master)
        self.frame.pack(pady=10)

        self.script_label = tk.Label(self.frame, text="Select Script:")
        self.script_label.grid(row=0, column=0, padx=5, pady=5)

        self.script_var = tk.StringVar()
        self.script_dropdown = ttk.Combobox(self.frame, textvariable=self.script_var, state="readonly", width=30)
        self.script_dropdown['values'] = [script['name'] for script in self.script_config['scripts']]
        self.script_dropdown.grid(row=0, column=1, padx=5, pady=5)
        self.script_dropdown.set(self.script_config['scripts'][0]['name'])  # Set default value

        self.log_text = tk.Text(master, wrap=tk.WORD, width=60, height=20)
        self.log_text.pack(padx=10, pady=10)

        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)

        self.run_button = tk.Button(button_frame, text="Run Script", command=self.run_script)
        self.run_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(button_frame, text="Stop Script", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = tk.Button(button_frame, text="Clear Log", command=self.clear_log)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.copy_button = tk.Button(button_frame, text="Copy Log", command=self.copy_log)
        self.copy_button.pack(side=tk.LEFT, padx=5)

        self.back_button = tk.Button(button_frame, text="Back", command=self.go_back)
        self.back_button.pack(side=tk.LEFT, padx=5)

        self.process = None
        self.output_queue = queue.Queue()
        self.stop_output_thread = threading.Event()

    def load_script_config(self):
        try:
            with open('scripts_config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Error", "scripts_config.json not found!")
            return {"scripts": []}
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON in scripts_config.json!")
            return {"scripts": []}

    def get_selected_script_filename(self):
        selected_name = self.script_var.get()
        for script in self.script_config['scripts']:
            if script['name'] == selected_name:
                return script['filename']
        return None

    def run_script(self):
        script_filename = self.get_selected_script_filename()
        if not script_filename:
            messagebox.showerror("Error", "No script selected!")
            return

        self.script_path = os.path.join(os.getcwd(), script_filename)
        if not os.path.exists(self.script_path):
            messagebox.showerror("Error", f"Script file not found: {self.script_path}")
            return

        # Disable the run button and enable the stop button
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Clear the log before running
        self.clear_log()

        # Start the script in a separate thread
        threading.Thread(target=self._run_script_thread, daemon=True).start()

        # Start the output handling thread
        self.stop_output_thread.clear()
        threading.Thread(target=self._handle_output, daemon=True).start()

    def _run_script_thread(self):
        try:
            # Set the PYTHONUNBUFFERED environment variable
            my_env = os.environ.copy()
            my_env["PYTHONUNBUFFERED"] = "1"

            # Run the script and capture its output
            self.process = subprocess.Popen([sys.executable, "-u", self.script_path],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            universal_newlines=True,
                                            env=my_env)

            # Read the output line by line
            for line in iter(self.process.stdout.readline, ''):
                if self.process is None:  # Check if process has been stopped
                    break
                self.output_queue.put(line.strip())

            # Wait for the process to complete
            if self.process:
                self.process.wait()
                self.output_queue.put("Script execution completed.")
        except Exception as e:
            self.output_queue.put(f"Error running script: {str(e)}")
        finally:
            self.process = None
            # Re-enable the run button and disable the stop button
            self.master.after(0, self._reset_buttons)

    def _handle_output(self):
        while not self.stop_output_thread.is_set():
            try:
                message = self.output_queue.get(block=False)
                self.log(message)
            except queue.Empty:
                self.master.after(100, self._handle_output)
                return

        # Process any remaining items in the queue
        while not self.output_queue.empty():
            message = self.output_queue.get()
            self.log(message)

    def stop_script(self):
        if self.process:
            self.process.terminate()
            self.process = None
            self.log("Script execution stopped.")
            self._reset_buttons()
        self.stop_output_thread.set()

    def _reset_buttons(self):
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def log(self, message):
        self.master.after(0, self._log, message)

    def _log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # Scroll to the end of the text

    def clear_log(self):
        self.log_text.delete('1.0', tk.END)

    def copy_log(self):
        log_content = self.log_text.get('1.0', tk.END)
        pyperclip.copy(log_content)
        self.log("Log content copied to clipboard.")

    def go_back(self):
        self.master.destroy()
        self.parent.deiconify()  # Show the parent window

if __name__ == "__main__":
    login_root = tk.Tk()
    login_app = LoginWindow(login_root)
    login_root.mainloop()
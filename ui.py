import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import threading
import pyperclip
import queue
import os

class LoginWindow:
    def __init__(self, master):
        self.master = master
        master.title("ProCodeOne - Login")
        master.geometry("300x150")
        master.resizable(False, False)

        self.frame = tk.Frame(master)
        self.frame.pack(pady=20)

        self.username_label = tk.Label(self.frame, text="Username:")
        self.username_label.grid(row=0, column=0, sticky="e")
        self.username_entry = tk.Entry(self.frame)
        self.username_entry.grid(row=0, column=1)

        self.password_label = tk.Label(self.frame, text="Password:")
        self.password_label.grid(row=1, column=0, sticky="e")
        self.password_entry = tk.Entry(self.frame, show="*")
        self.password_entry.grid(row=1, column=1)

        self.login_button = tk.Button(self.frame, text="Login", command=self.login)
        self.login_button.grid(row=2, column=1, pady=10)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if username == "aman2929" and password == "qwerty":
            self.master.destroy()
            root = tk.Tk()
            app = ScriptRunnerApp(root)
            root.mainloop()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

class ScriptRunnerApp:
    def __init__(self, master):
        self.master = master
        master.title("ProCodeOne - TradeBotOne")
        master.geometry("500x400")
        master.resizable(False, False)  # Disable window resizing

        # Path to your script
        self.script_path = "test.py"  # Replace with actual path

        # Create and pack the text widget for logging
        self.log_text = tk.Text(master, wrap=tk.WORD, width=60, height=20)
        self.log_text.pack(padx=10, pady=10)

        # Frame for buttons
        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)

        # Create and pack the run button
        self.run_button = tk.Button(button_frame, text="Run Script", command=self.run_script)
        self.run_button.pack(side=tk.LEFT, padx=5)

        # Create and pack the stop button
        self.stop_button = tk.Button(button_frame, text="Stop Script", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Create and pack the clear button
        self.clear_button = tk.Button(button_frame, text="Clear Log", command=self.clear_log)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # Create and pack the copy button
        self.copy_button = tk.Button(button_frame, text="Copy Log", command=self.copy_log)
        self.copy_button.pack(side=tk.LEFT, padx=5)

        self.process = None
        self.output_queue = queue.Queue()
        self.stop_output_thread = threading.Event()

    def run_script(self):
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

if __name__ == "__main__":
    login_root = tk.Tk()
    login_app = LoginWindow(login_root)
    login_root.mainloop()
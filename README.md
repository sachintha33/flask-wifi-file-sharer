# WiFi Drop - A High-Speed Local File Sharing Web App

![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)

A simple, yet powerful web application built with Python and Flask to transfer very large files (GBs) seamlessly between devices on the same local network.

This project was created to solve the common issue of file size limitations in standard web servers, allowing for the transfer of gigabyte-sized files without crashing the server or consuming excessive memory.

## 🚀 Features

-   **Large File Support:** Transfer files of virtually any size (tested up to 10GB+).
-   **Chunked Uploads:** Files are split into small chunks (e.g., 5MB) and sent sequentially, ensuring low server memory usage.
-   **Reliable Transfers:** The chunking mechanism makes the upload process resilient to minor network interruptions.
-   **Real-time Progress:** A clean user interface with a progress bar to monitor uploads, powered by Dropzone.js.
-   **Simple & Fast:** Minimal setup required. Just run the server and connect from any device on the same WiFi network.
-   **Cross-Platform:** Works on any device with a modern web browser (Windows, macOS, Linux, Android, iOS).

## 💡 The Problem It Solves

Standard web frameworks often load the entire uploaded file into memory. This works for small files but quickly leads to server crashes when a user tries to upload a large file (e.g., >100MB). This application bypasses that limitation by processing the file as a stream of small chunks, ensuring stable performance regardless of file size.

## 🛠️ Tech Stack

-   **Backend:** Python 3, Flask
-   **Frontend:** HTML5, JavaScript
-   **JavaScript Library:** [Dropzone.js](https://www.dropzone.dev/) for handling the client-side chunking and UI.

## ⚙️ Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites

-   Python 3.6 or higher
-   `pip` (Python package installer)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/flask-wifi-file-sharer.git
    cd flask-wifi-file-sharer
    ```
    *(Replace `your-username` with your actual GitHub username)*

2.  **Create a virtual environment (recommended):**
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Flask application:**
    ```bash
    python app.py
    ```

5.  **Access the application:**
    -   The server will start, typically on `http://0.0.0.0:5000`.
    -   Find your computer's local IP address (e.g., `192.168.1.10`). You can find this by running `ipconfig` on Windows or `ifconfig` on macOS/Linux.
    -   Open a web browser on any other device connected to the same WiFi network and navigate to `http://<YOUR_COMPUTER_IP>:5000`. For example: `http://192.168.1.10:5000`.

You should now see the file upload interface. Enjoy sharing large files with ease!

## 🖼️ Screenshot

*(Optional: Add a screenshot of your application here. You can upload an image to your GitHub repo and link it)*

![App Screenshot](link-to-your-screenshot.png)

## 📜 License

This project is licensed under the MIT License - see the `LICENSE` file for details. *(You can choose to add a LICENSE file if you want)*.

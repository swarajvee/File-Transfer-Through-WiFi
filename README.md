# File-Transfer-Through-WiFi  
Easily send and receive files with others on the same WiFi network.  

## Installation  
1. Download the directory or clone it using:  
```sh
git clone https://github.com/swarajvee/File-Transfer-Through-WiFi.git
```
2. Open a terminal inside this directory.  

3. Install the required Python packages:  
```sh
pip install -r requirements.txt
```

## Usage  
4. Run the script using (press tab for autocompletion):  
```sh
python fileTransfer.py
```
The code will display an HTTP link with two IP addresses: one is the local IP of your machine, and the other is the network IP.  

5. Open the HTTP link associated with the network IP (the second one) to start the file transfer.  

## Notes  
- Shared files are stored in the `shared_files` folder inside the code directory.  
- The script automatically removes all previously shared files and the QR code when restarted.  
- You can manually delete the `shared_files` folder if needed (I recommend running the script again to clear the `shared_files` directory).  

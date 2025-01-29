# File-Transfer-Through-WiFi  
Easily send and receive files with others on the same WiFi network.  

## Installation  
Download the directory or clone it using:  
```sh
git clone https://github.com/swarajvee/File-Transfer-Through-WiFi.git
```
Then install the required Python packages:  
```sh
pip install -r requirements.txt
```

## Usage  
Run the script using:  
```sh
python path/to/dir/fileTransfer.py
```
The code will display an HTTP link with two IP addresses: one is the local IP of your machine, and the other is the network IP. Open the HTTP link associated with the network IP (second one) to start the file transfer.  

## Notes  
- Shared files are stored in the `shared_files` folder inside the code directory.  
- The script automatically removes all previously shared files and the QR code when restarted.  
- You can manually delete the `shared_files` folder if needed (I recommend running the script again to clear the `shared_files` directory).  

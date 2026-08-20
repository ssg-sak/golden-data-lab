import os
import urllib.request

def download_online_retail_data():
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00502/online_retail_II.xlsx"
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Define the output path (data/raw/online_retail_II.xlsx)
    output_dir = os.path.join(current_dir, "..", "data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "online_retail_II.xlsx")
    
    print(f"Downloading from {url}...")
    print(f"Saving to {output_path}...")
    
    try:
        urllib.request.urlretrieve(url, output_path)
        print("Download completed successfully!")
    except Exception as e:
        print(f"Error downloading the file: {e}")

if __name__ == "__main__":
    download_online_retail_data()

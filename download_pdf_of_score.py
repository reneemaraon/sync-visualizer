import requests
from PIL import Image

# Constants
ID = 68
TOTAL_PAGES = 11
URL_TEMPLATE = "https://weefeen-user-data.eu-central-1.linodeobjects.com/staging/score/{id}/{page}.jpg"
OUTPUT_PDF = "output.pdf"

# Download images
images = []
for page in range(TOTAL_PAGES):
    url = URL_TEMPLATE.format(id=ID, page=page)
    response = requests.get(url, stream=True)
    
    if response.status_code == 200:
        img = Image.open(response.raw).convert("RGB")
        images.append(img)
        print(f"Downloaded page {page}")
    else:
        print(f"Failed to download page {page}")

# Save as PDF
if images:
    images[0].save(OUTPUT_PDF, save_all=True, append_images=images[1:])
    print(f"PDF saved as {OUTPUT_PDF}")
else:
    print("No images downloaded.")

#%%
import requests
from bs4 import BeautifulSoup
import pandas as pd
from time import sleep

output_path = "D:/DS_Portafolio/ubika/data/raw/properati/adondevivir_todo.csv"


base_url = "https://www.properati.com.pe/s/lima/alquiler/{page}?propertyType=apartment%2Chouse"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
max_pages = 1  # Máximo de páginas a scrapear (ajusta según necesidad)
data = []
#%%
print("🚀 Iniciando scraping de Properati...")

for page in range(1, 5):
    url = base_url.format(page=page)
    print(f"📖 Extrayendo página {page}...")

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error en página {page}. Saltando...")
        continue

    soup = BeautifulSoup(response.text, 'html.parser')
    properties = soup.find_all('article', class_='snippet')

    for prop in properties:
        title_link = prop.find('a', class_='title')
        name = title_link.get_text(strip=True) if title_link else "N/A"
        url = title_link['href'] if title_link else "N/A"
        
        price = prop.find('div', class_='price').get_text(strip=True) if prop.find('div', class_='price') else "N/A"
        location = prop.find('div', class_='location').get_text(strip=True) if prop.find('div', class_='location') else "N/A"
        
        bedrooms = prop.find('span', class_='properties__bedrooms').get_text(strip=True) if prop.find('span', class_='properties__bedrooms') else "N/A"
        bathrooms = prop.find('span', class_='properties__bathrooms').get_text(strip=True) if prop.find('span', class_='properties__bathrooms') else "N/A"
        area = prop.find('span', class_='properties__area').get_text(strip=True) if prop.find('span', class_='properties__area') else "N/A"

        data.append({
            "pagina": page,
            "nombre": name,
            "url": url,
            "precio": price,
            "ubicación": location,
            "dormitorios": bedrooms,
            "banios": bathrooms,
            "area": area
        })

    sleep(3)

df = pd.DataFrame(data)

df.to_csv(output_path, index=False)
print(f"✅ Scraping finalizado. Archivo guardado en:\n{output_path}")
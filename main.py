import json
import asyncio
import os
import webbrowser
import re
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://resultadosegundavuelta.onpe.gob.pe/main/presidenciales"

EXPORT_DIR = "exports"
TEMPLATE_DIR = "templates"

os.makedirs(EXPORT_DIR, exist_ok=True)

def load_html_template():
    template_path = os.path.join(TEMPLATE_DIR, "dashboard.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

def timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

async def scrape_onpe_results():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-web-security",
            ]
        )
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-PE', 'es', 'en'] });
        """)
        
        print(f"Conectando a {URL}...")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector("app-generic-filter-ubigeo", timeout=30000)
        
        results = []
        region_select = page.locator('mat-select[formcontrolname="region"]')
        
        # 1. Procesar ámbito Extranjero
        print("Extrayendo datos de Extranjero...")
        await region_select.click()
        await page.wait_for_selector(".mat-mdc-select-panel")
        await page.get_by_role("option", name="EXTRANJERO", exact=True).click()
        await page.wait_for_timeout(2000)
        
        extranjero_data = await extract_current_page_data(page, "Extranjero")
        results.append(extranjero_data)

        # 2. Procesar ámbito Nacional (Perú)
        await region_select.click()
        await page.wait_for_selector(".mat-mdc-select-panel")
        await page.get_by_role("option", name="PERÚ", exact=True).click()
        await page.wait_for_timeout(1000)

        # Abrimos el selector de Departamentos para obtener la lista
        dept_select = page.locator('mat-select[formcontrolname="department"]')
        await dept_select.click()
        await page.wait_for_selector(".mat-mdc-select-panel")
        
        dept_options = await page.locator(".mat-mdc-select-panel mat-option").all_text_contents()
        
        # Filtrado estricto de las opciones
        departments = [
            d.strip() for d in dept_options 
            if d.strip() and "DEPARTAMENTO" not in d.upper() and "REGIÓN" not in d.upper() and "REGION" not in d.upper()
        ]
        
        # Cerramos el menú para iniciar el bucle limpiamente
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

        for dept in departments:
            print(f"Extrayendo datos de la región: {dept}...")
            
            # Forzamos el click en el desplegable y esperamos que aparezca el panel
            await dept_select.click()
            await page.wait_for_selector(".mat-mdc-select-panel", state="visible")
            
            # Solución definitiva usando el rol nativo de accesibilidad
            option_locator = page.get_by_role("option", name=dept, exact=True)
            await option_locator.scroll_into_view_if_needed() 
            await option_locator.click()
            
            # Esperamos a que los datos de la página cambien/se actualicen
            await page.wait_for_timeout(2000) 
            
            dept_data = await extract_current_page_data(page, dept)
            results.append(dept_data)

        ts = timestamp_str()

        json_filename = f"resultados_onpe_{ts}.json"
        json_path = os.path.join(EXPORT_DIR, json_filename)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        print(f"JSON guardado: {json_path}")
        print("¡Extracción completada! Generando Dashboard HTML...")
        
        json_data = json.dumps(results, ensure_ascii=False)
        html_template = load_html_template()
        html_content = html_template.replace("{{JSON_DATA}}", json_data)
        
        html_filename = f"dashboard_onpe_{ts}.html"
        html_path = os.path.abspath(os.path.join(EXPORT_DIR, html_filename))
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"Dashboard generado: {html_path}")
        print(f"Abriendo el dashboard interactivo en tu navegador...")
        webbrowser.open(f"file://{html_path}")
        
        await browser.close()


async def extract_current_page_data(page, region_name):
    # Usamos evaluate para acceder al DOM directamente
    # Esta lógica busca los elementos dentro de la lista de leyenda (ul)
    data = await page.evaluate("""() => {
        const leyendas = document.querySelectorAll('ul.leyenda.vertical li');
        let envioJEE = "0 %";
        let pendientes = "0 %";

        leyendas.forEach(li => {
            const texto = li.innerText.toLowerCase();
            const h3 = li.querySelector('h3');
            if (h3) {
                if (texto.includes('envío al jee') || texto.includes('envio jee')) {
                    envioJEE = h3.innerText.trim();
                } else if (texto.includes('pendientes')) {
                    pendientes = h3.innerText.trim();
                }
            }
        });

        // Total de actas usando Regex sobre el contenedor principal
        const contenedor = document.querySelector('.sombra-resumen-acta.version-pc').innerText;
        const totalMatch = contenedor.match(/Total de actas:\s*([\d,']+)/);
        
        return {
            total: totalMatch ? totalMatch[1].replace(/[,']/g, '') : "0",
            contabilizadas: document.querySelector('.sombra-resumen-acta.version-pc b').innerText.trim(),
            envioJEE: envioJEE,
            pendientes: pendientes
        };
    }""")

    # Extracción de candidatos (mantiene tu lógica previa)
    candidates_cards = await page.locator("onpe-card-candidate").all()
    candidatos_list = []
    
    for card in candidates_cards:
        nombre = await card.locator(".tarjeta-candidato__nombre").inner_text()
        partido = await card.locator(".tarjeta-candidato__organizacion").inner_text()
        votos_raw = await card.locator(".tarjeta-candidato__valor").inner_text()
        votos = votos_raw.replace("'", "").replace(",", "").strip()
        
        validos_pct = await card.locator('.tarjeta-candidato__fila-dato:has-text("Votos válidos:") strong').inner_text()
        emitidos_pct = await card.locator('.tarjeta-candidato__fila-dato:has-text("Votos emitidos:") strong').inner_text()
        
        candidatos_list.append({
            "nombre": nombre.strip(),
            "partido": partido.strip(),
            "votos": votos,
            "votosValidos": validos_pct.strip(),
            "votosEmitidos": emitidos_pct.strip()
        })

    return {
        "region": region_name,
        "actas": data,
        "candidatos": candidatos_list
    }


if __name__ == "__main__":
    asyncio.run(scrape_onpe_results())
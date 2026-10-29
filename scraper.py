"""
Script to extract course details from CTT FISEI UTA website.
"""
import urllib.request
import re
import json
import ssl
from html import unescape

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

course_ids = [16, 17, 18, 19, 20, 21, 13, 15, 14, 9, 1, 2, 3, 4, 5, 6, 7, 8]

def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    return ' '.join(text.split())

def scrape_course(cid):
    url = f"https://ctt-talleresfisei.uta.edu.ec/curso{cid}.php"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

    # Title
    title_m = re.search(r'<h1 class=["\']tituloCurso["\']>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    title = clean_html(title_m.group(1)) if title_m else f"Curso {cid}"

    # Description
    desc_m = re.search(r'<h2>DESCRIPCI[ÓO]N</h2>\s*<p>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    desc = clean_html(desc_m.group(1)) if desc_m else ""

    # Objectives
    obj_m = re.search(r'<h2>OBJETIVOS</h2>\s*<ul>(.*?)</ul>', html, re.DOTALL | re.IGNORECASE)
    objectives = []
    if obj_m:
        lis = re.findall(r'<li>(.*?)</li>', obj_m.group(1), re.DOTALL)
        objectives = [clean_html(li) for li in lis if li.strip()]

    # Location / Lugar
    loc_m = re.search(r'<h2>LUGAR DE CELEBRACI[ÓO]N</h2>\s*<ul>(.*?)</ul>', html, re.DOTALL | re.IGNORECASE)
    location = []
    if loc_m:
        lis = re.findall(r'<li>(.*?)</li>', loc_m.group(1), re.DOTALL)
        location = [clean_html(li) for li in lis if li.strip()]

    # Instructors / Committee
    inst_m = re.search(r'<h2>INSTRUCTORES</h2>\s*<ul>(.*?)</ul>', html, re.DOTALL | re.IGNORECASE)
    instructors = []
    if inst_m:
        lis = re.findall(r'<li>(.*?)</li>', inst_m.group(1), re.DOTALL)
        instructors = [clean_html(li) for li in lis if li.strip()]

    # Tab 1: Requirements & Details
    tab1_m = re.search(r'<div class=["\']tab1["\']>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    details = {}
    if tab1_m:
        t1_content = tab1_m.group(1)
        items = re.findall(r'<li>(.*?)</li>', t1_content, re.DOTALL)
        current_key = "general"
        for it in items:
            strong_m = re.search(r'<strong>(.*?):?</strong>\s*(.*)', it, re.DOTALL)
            if strong_m:
                k = clean_html(strong_m.group(1)).rstrip(':')
                v = clean_html(strong_m.group(2))
                details[k] = v
                current_key = k
            else:
                cleaned = clean_html(it)
                if "$" in cleaned:
                    details.setdefault("Precios_Detalle", []).append(cleaned)
                elif cleaned:
                    details.setdefault("Otros_Detalles", []).append(cleaned)

    # Tab 2: Materials & Equipments
    tab2_m = re.search(r'<div class=["\']tab2["\']>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    materials = []
    if tab2_m:
        lis = re.findall(r'<li>(.*?)</li>', tab2_m.group(1), re.DOTALL)
        materials = [clean_html(li) for li in lis if li.strip()]

    # Tab 3: Syllabus / Contenidos
    tab3_m = re.search(r'<div class=["\']tab3["\']>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    syllabus = []
    if tab3_m:
        t3 = tab3_m.group(1)
        # Find main items or modules
        mods = re.findall(r'<strong>(.*?):?</strong>(.*?)(?=<strong>|$)', t3, re.DOTALL)
        if mods:
            for mod_title, mod_body in mods:
                sub_items = [clean_html(x) for x in re.findall(r'<li>(.*?)</li>', mod_body, re.DOTALL)]
                syllabus.append({
                    "modulo": clean_html(mod_title),
                    "temas": sub_items or [clean_html(mod_body)]
                })
        else:
            lis = re.findall(r'<li>(.*?)</li>', t3, re.DOTALL)
            syllabus = [{"modulo": f"Tema {i+1}", "temas": [clean_html(li)]} for i, li in enumerate(lis)]

    # Registration link
    reg_m = re.search(r'href=["\'](https://docs\.google\.com/forms/[^"\']+)["\']', html)
    reg_url = reg_m.group(1) if reg_m else "https://ctt-talleresfisei.uta.edu.ec/contact.php"

    course_data = {
        "id": cid,
        "code": f"CTT-FISEI-{cid:02d}",
        "title": title,
        "url": url,
        "description": desc,
        "objectives": objectives,
        "location": location or ["Campus Huachi, Ambato", "Virtual"],
        "instructors": instructors,
        "details": details,
        "materials": materials,
        "syllabus": syllabus,
        "registration_url": reg_url,
        "status": "ABIERTO" if cid in [16, 17, 18, 19, 20, 21, 13, 14, 15] else "CERRADO"
    }
    return course_data

if __name__ == "__main__":
    courses = []
    for cid in course_ids:
        print(f"Scraping course {cid}...")
        c = scrape_course(cid)
        if c and c["title"] and "No title" not in c["title"]:
            courses.append(c)
    
    with open("courses_catalog.json", "w", encoding="utf-8") as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)
    print(f"Scraped {len(courses)} courses successfully.")

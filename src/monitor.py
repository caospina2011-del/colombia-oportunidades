#!/usr/bin/env python3
"""
Sistema de Monitoreo de Licitaciones - Colombia Compra Eficiente
Consulta API datos.gov.co, filtra, hace scoring y genera reporte
"""

import json
import requests
import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
import re

# Configuración
DATOS_GOV_API = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
LIMIT_RESULTS = 20
MIN_BUDGET = 150000000
MAX_BUDGET = 800000000

class LicitacionScorer:
    def __init__(self, company_profile: Dict, scoring_config: Dict):
        self.company = company_profile
        self.scoring = scoring_config
        self.keywords = set(k.lower() for k in company_profile.get('keyword_vector', []))
        
    def apply_hard_filters(self, licitacion: Dict) -> bool:
        """Filtros duros antes de análisis semántico"""
        try:
            # Extraer presupuesto
            precio_str = str(licitacion.get('precio_estimado', '0')).replace(',', '').replace('.', '')
            precio = int(precio_str) if precio_str.isdigit() else 0
            
            # Filtro de presupuesto
            if precio < MIN_BUDGET or precio > MAX_BUDGET:
                return False
            
            # Verificar que requiera ejecución técnica (no solo consultoría)
            objeto = str(licitacion.get('objeto_del_proceso', '')).lower()
            exclusiones = ['consultoría', 'estudios de', 'asesoría', 'asesoria', 'elaboración de informes']
            if all(exc in objeto for exc in ['consultoría']):
                return False
                
            return True
        except:
            return False
    
    def calculate_score(self, licitacion: Dict) -> tuple:
        """Calcula score de 0-100 y clasificación"""
        score = 0
        details = []
        
        objeto = str(licitacion.get('objeto_del_proceso', '')).lower()
        entidad = str(licitacion.get('nombre_entidad', '')).lower()
        departamento = str(licitacion.get('departamento_entidad', '')).lower()
        modalidad = str(licitacion.get('modalidad_de_contratacion', '')).lower()
        
        # 1. Afinidad técnica (30 puntos)
        tech_score = 0
        if any(kw in objeto for kw in ['media tensión', 'subestación', 'transformador']):
            tech_score += 10
            details.append("Media tensión (+10)")
        if any(kw in objeto for kw in ['eléctrico', 'electricidad', 'instalación eléctrica']):
            tech_score += 8
            details.append("Electricidad (+8)")
        if any(kw in objeto for kw in ['mantenimiento', 'preventivo', 'correctivo']):
            tech_score += 5
            details.append("Mantenimiento (+5)")
        if any(kw in objeto for kw in ['construcción', 'obra civil']):
            tech_score += 4
            details.append("Construcción (+4)")
        if any(kw in objeto for kw in ['redes', 'telecomunicaciones', 'cableado']):
            tech_score += 3
            details.append("Telecom (+3)")
        score += min(tech_score, 30)
        
        # 2. Alineación presupuestal (20 puntos)
        try:
            precio_str = str(licitacion.get('precio_estimado', '0')).replace(',', '').replace('.', '')
            precio = int(precio_str)
            target_min = self.company['financial_profile']['target_contract_value_min_cop']
            target_max = self.company['financial_profile']['target_contract_value_max_cop']
            
            if target_min <= precio <= target_max:
                score += 20
                details.append("Presupuesto óptimo (+20)")
            elif precio * 0.8 <= target_min or precio <= target_max * 1.2:
                score += 12
                details.append("Presupuesto aceptable (+12)")
        except:
            pass
        
        # 3. Geográfico (10 puntos)
        if 'bogotá' in departamento:
            score += 10
            details.append("Bogotá (+10)")
        elif 'cundinamarca' in departamento:
            score += 8
            details.append("Cundinamarca (+8)")
        elif self.company['geographical_scope']['national_coverage']:
            score += 6
            details.append("Nacional (+6)")
        
        # 4. Modalidad (10 puntos)
        if 'licitación pública' in modalidad:
            score += 10
            details.append("Licitación pública (+10)")
        elif 'selección abreviada' in modalidad:
            score += 8
            details.append("Selección abreviada (+8)")
        elif 'mínima cuantía' in modalidad:
            score += 5
            details.append("Mínima cuantía (+5)")
        
        # 5. Tipo de entidad (10 puntos)
        if any(e in entidad for e in ['energía', 'electrificadora', 'eepm', 'enel']):
            score += 10
            details.append("Sector energía (+10)")
        elif any(e in entidad for e in ['infraestructura', 'metro', 'transmilenio']):
            score += 8
            details.append("Infraestructura (+8)")
        elif any(e in entidad for e in ['industria', 'fábrica', 'empresa']):
            score += 7
            details.append("Industrial (+7)")
        elif any(e in entidad for e in ['distrital', 'secretaría', 'alcaldía']):
            score += 5
            details.append("Entidad pública (+5)")
        
        # 6. Keywords adicionales (bono)
        keyword_matches = sum(1 for kw in self.keywords if kw in objeto)
        if keyword_matches >= 3:
            score += 5
            details.append("Múltiples keywords (+5)")
        
        # Clasificación
        if score >= 75:
            priority = "Alta"
        elif score >= 55:
            priority = "Media"
        else:
            priority = "Baja"
            
        return min(score, 100), priority, details

def fetch_licitaciones() -> List[Dict]:
    """Consulta API de datos.gov.co"""
    try:
        # Consulta con filtros de presupuesto
        query = f"""
        SELECT proceso_de_compra, objeto_del_proceso, nombre_entidad, 
               departamento_entidad, precio_estimado, modalidad_de_contratacion,
               fecha_de_publicacion_del_proceso, url_proceso_en_secop_i
        WHERE precio_estimado >= {MIN_BUDGET} 
        AND precio_estimado <= {MAX_BUDGET}
        AND estado_del_proceso = 'Activo'
        ORDER BY fecha_de_publicacion_del_proceso DESC
        LIMIT {LIMIT_RESULTS}
        """
        
        response = requests.get(
            DATOS_GOV_API,
            params={"$query": query},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error consultando API: {e}")
        return []

def generate_html_report(licitaciones_scored: List[tuple], run_date: str) -> str:
    """Genera reporte HTML ordenado por score"""
    # Ordenar por score descendente
    sorted_results = sorted(licitaciones_scored, key=lambda x: x[1], reverse=True)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .oportunidad {{ background: white; margin: 15px 0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .alta {{ border-left: 5px solid #27ae60; }}
            .media {{ border-left: 5px solid #f39c12; }}
            .baja {{ border-left: 5px solid #e74c3c; }}
            .score {{ font-size: 24px; font-weight: bold; float: right; }}
            .score-alta {{ color: #27ae60; }}
            .score-media {{ color: #f39c12; }}
            .score-baja {{ color: #e74c3c; }}
            .details {{ color: #666; font-size: 12px; margin-top: 10px; }}
            .budget {{ font-size: 18px; color: #2c3e50; font-weight: bold; }}
            .entity {{ color: #7f8c8d; }}
            a {{ color: #3498db; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Oportunidades de Contratación - SD Soluciones Integrales</h1>
            <p>Reporte generado: {run_date}</p>
            <p>Total oportunidades analizadas: {len(sorted_results)}</p>
        </div>
    """
    
    for lic, score, priority, details in sorted_results:
        proc_id = lic.get('proceso_de_compra', 'N/A')
        objeto = lic.get('objeto_del_proceso', 'Sin descripción')
        entidad = lic.get('nombre_entidad', 'Sin entidad')
        precio = lic.get('precio_estimado', '0')
        url = lic.get('url_proceso_en_secop_i', '#')
        modalidad = lic.get('modalidad_de_contratacion', 'No especificada')
        
        # Formatear precio
        try:
            precio_num = int(str(precio).replace(',', '').replace('.', ''))
            precio_fmt = f"${precio_num:,.0f} COP"
        except:
            precio_fmt = str(precio)
        
        score_class = f"score-{priority.lower()}"
        priority_class = priority.lower()
        details_str = " | ".join(details) if details else "Sin detalles adicionales"
        
        html += f"""
        <div class="oportunidad {priority_class}">
            <div class="score {score_class}">{score}/100</div>
            <h3>{objeto[:100]}{'...' if len(objeto) > 100 else ''}</h3>
            <p class="entity">🏢 {entidad}</p>
            <p class="budget">💰 {precio_fmt}</p>
            <p>📋 Modalidad: {modalidad}</p>
            <p>🔗 <a href="{url}" target="_blank">Ver proceso en SECOP</a></p>
            <p>🆔 ID: {proc_id}</p>
            <div class="details">📈 Factores: {details_str}</div>
        </div>
        """
    
    html += """
    </body>
    </html>
    """
    
    return html

def send_email(html_content: str, recipient: str, run_date: str):
    """Envía correo con reporte HTML"""
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "caospina2011@gmail.com"
        sender_password = os.environ.get('EMAIL_PASSWORD')  # Secret de GitHub
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Oportunidades SECOP - {run_date}"
        msg['From'] = sender_email
        msg['To'] = recipient
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"✅ Correo enviado a {recipient}")
        return True
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")
        return False

def main():
    print("🚀 Iniciando monitoreo de licitaciones...")
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Cargar configuraciones
    with open('config/company_profile.json', 'r', encoding='utf-8') as f:
        company_profile = json.load(f)
    
    with open('config/scoring_config.json', 'r', encoding='utf-8') as f:
        scoring_config = json.load(f)
    
    scorer = LicitacionScorer(company_profile, scoring_config)
    
    # Consultar licitaciones
    print("📡 Consultando API datos.gov.co...")
    licitaciones = fetch_licitaciones()
    print(f"📋 {len(licitaciones)} licitaciones encontradas")
    
    # Filtrar y hacer scoring
    results = []
    for lic in licitaciones:
        if scorer.apply_hard_filters(lic):
            score, priority, details = scorer.calculate_score(lic)
            results.append((lic, score, priority, details))
            print(f"  ✓ {lic.get('proceso_de_compra', 'N/A')}: {score}/100 ({priority})")
    
    print(f"\n🎯 {len(results)} oportunidades calificadas")
    
    # Generar reporte
    html_report = generate_html_report(results, run_date)
    
    # Guardar localmente
    os.makedirs('data', exist_ok=True)
    with open(f'data/reporte_{datetime.now().strftime("%Y%m%d")}.html', 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    # Enviar por correo
    recipient = os.environ.get('REPORT_EMAIL', 'caospina2011@gmail.com')
    if send_email(html_report, recipient, run_date):
        print("✅ Proceso completado exitosamente")
    else:
        print("⚠️ Reporte generado pero no se pudo enviar correo")

if __name__ == "__main__":
    main()
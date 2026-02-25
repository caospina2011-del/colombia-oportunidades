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

# Configuración - API SECOP I (datos.gov.co) - Contratos grandes
DATOS_GOV_API = "https://www.datos.gov.co/resource/rpmr-utcd.json"
LIMIT_RESULTS = 20
MIN_BUDGET = 150000000  # 150 millones mínimo (obras más pequeñas)
MAX_BUDGET = 2000000000  # 2 mil millones máximo (más flexible)
MIN_SCORE = 55  # Score mínimo más permisivo para captar oportunidades variadas

class LicitacionScorer:
    def __init__(self, company_profile: Dict, scoring_config: Dict):
        self.company = company_profile
        self.scoring = scoring_config
        self.keywords = set(k.lower() for k in company_profile.get('keyword_vector', []))
        
    def apply_hard_filters(self, licitacion: Dict) -> bool:
        """Filtros duros antes de análisis semántico"""
        try:
            # Extraer presupuesto (campo: valor_contrato en SECOP I)
            precio_raw = licitacion.get('valor_contrato', '0')
            if isinstance(precio_raw, (int, float)):
                precio = int(precio_raw)
            else:
                precio_str = str(precio_raw).replace(',', '').replace('.', '')
                precio = int(precio_str) if precio_str.isdigit() else 0
            
            # Filtro de presupuesto (150M a 2,000M)
            if precio < MIN_BUDGET or precio > MAX_BUDGET:
                return False
            
            # Filtro de fecha: últimos 120 días (más permisivo para captar más oportunidades)
            fecha_pub = licitacion.get('fecha_de_firma_del_contrato', '')
            if fecha_pub:
                from datetime import datetime, timedelta
                try:
                    # Parsear fecha (formato ISO)
                    fecha_proceso = datetime.fromisoformat(fecha_pub.replace('Z', '+00:00').replace('T', ' ').split('.')[0])
                    ciento_veinte_dias_atras = datetime.now() - timedelta(days=120)
                    if fecha_proceso < ciento_veinte_dias_atras:
                        return False
                except:
                    pass  # Si no puede parsear, deja pasar
            
            # Verificar que requiera ejecución técnica (no solo consultoría pura)
            objeto = str(licitacion.get('objeto_del_proceso', '')).lower()
            
            # Exclusiones fuertes
            exclusiones_fuertes = [
                'transporte de material', 'transporte de pétreo', 'transporte de agregados',
                'consultoria sin ejecucion', 'asesoria exclusivamente juridica',
                'estudio de factibilidad sin ejecucion', 'minería', 'exploración minera',
                'consultoria pura', 'solo estudios', 'solo asesoria'
            ]
            if any(exc in objeto for exc in exclusiones_fuertes):
                return False
                
            return True
        except Exception as e:
            print(f"Error en filtro: {e}")
            return False
    
    def calculate_score(self, licitacion: Dict) -> tuple:
        """Calcula score de 0-100 y clasificación"""
        score = 0
        details = []
        
        objeto = str(licitacion.get('objeto_del_proceso', '')).lower()
        entidad = str(licitacion.get('nombre_de_la_entidad', '')).lower()
        departamento = str(licitacion.get('departamento_entidad', '')).lower()
        modalidad = str(licitacion.get('modalidad_de_contrataci_n', '')).lower()
        
        # 1. Afinidad técnica (40 puntos) - Eléctrico + Obras civiles
        tech_score = 0
        has_electric = False
        has_civil = False
        
        # Media tensión - core del negocio (máxima prioridad)
        if any(kw in objeto for kw in ['media tension', 'subestacion', 'transformador', 'redes de distribucion']):
            tech_score += 20
            details.append("Media tensión (+20)")
            has_electric = True
        
        # Baja tensión y electricidad general
        if any(kw in objeto for kw in ['baja tension', 'instalacion electrica', 'cableado estructurado', 
                                       'tableros electricos', 'alumbrado publico', 'cajas de derivacion',
                                       'puesta a tierra', 'red electrica', 'montaje electrico']):
            tech_score += 15
            details.append("Baja tensión/eléctrico (+15)")
            has_electric = True
        
        # Pruebas técnicas especializadas
        if any(kw in objeto for kw in ['pruebas vlf', 'termografia', 'aceite dielectrico']):
            tech_score += 12
            details.append("Pruebas técnicas (+12)")
            has_electric = True
        
        # Canalización subterránea (especialidad específica)
        if any(kw in objeto for kw in ['canalizacion subterranea', 'cajas cs276', 'cajas cs277', 'cajas cs280']):
            tech_score += 10
            details.append("Canalización subterránea (+10)")
            has_electric = True
        
        # HVAC
        if any(kw in objeto for kw in ['aire acondicionado', 'hvac', 'sistemas de extraccion', 'climatizacion']):
            tech_score += 12
            details.append("HVAC (+12)")
        
        # Obras civiles y construcción (importante para la empresa)
        if any(kw in objeto for kw in ['cubiertas', 'fachadas', 'remodelacion', 'ampliaciones']):
            if has_electric:
                tech_score += 12
                details.append("Remodelación con eléctrico (+12)")
            else:
                tech_score += 8
                details.append("Remodelación/cubiertas/fachadas (+8)")
            has_civil = True
        
        # Obra civil general (menor prioridad pero válida)
        if any(kw in objeto for kw in ['obra civil', 'construccion', 'edificaciones comerciales', 'acabados']):
            if not has_civil:  # Si no se contó ya
                if has_electric:
                    tech_score += 10
                    details.append("Obra civil con eléctrico (+10)")
                else:
                    tech_score += 5
                    details.append("Obra civil general (+5)")
                has_civil = True
        
        # Mantenimiento (eléctrico o general)
        if any(kw in objeto for kw in ['mantenimiento', 'preventivo', 'correctivo']):
            if has_electric or has_civil:
                tech_score += 6
                details.append("Mantenimiento especializado (+6)")
        
        score += min(tech_score, 40)
        
        # 2. Alineación presupuestal (25 puntos)
        try:
            precio_raw = licitacion.get('valor_contrato', '0')
            if isinstance(precio_raw, (int, float)):
                precio = int(precio_raw)
            else:
                precio = int(str(precio_raw).replace(',', '').replace('.', ''))
            
            # Rango ideal: 400M-600M (+25)
            # Rango aceptable: 300M-800M (+18)
            # Fuera de rango: +5
            if 400000000 <= precio <= 600000000:
                score += 25
                details.append("Presupuesto óptimo 400M-600M (+25)")
            elif 300000000 <= precio <= 800000000:
                score += 18
                details.append("Presupuesto aceptable 300M-800M (+18)")
            elif precio > 0:
                score += 5
                details.append("Presupuesto válido (+5)")
        except:
            pass
        
        # 3. Geográfico (20 puntos) - Bogotá y Cundinamarca cercano
        depto_lower = departamento.lower()
        if 'bogotá' in depto_lower or 'bogota' in depto_lower or 'distrito capital' in depto_lower:
            score += 20
            details.append("Bogotá D.C. (+20)")
        elif 'cundinamarca' in depto_lower:
            score += 18  # Aumentado - Cundinamarca es viable
            details.append("Cundinamarca cercano (+18)")
        elif self.company['geographical_scope']['national_coverage']:
            score += 3
            details.append("Nacional (+3)")
        
        # 4. Tipo de entidad (10 puntos)
        if any(e in entidad for e in ['epm', 'isa', 'codensa', 'electrificadora', 'energía']):
            score += 10
            details.append("Empresa energía (+10)")
        elif any(e in entidad for e in ['distrital', 'secretaría', 'alcaldía bogotá', 'idrd', 'umv']):
            score += 8
            details.append("Entidad distrital Bogotá (+8)")
        elif any(e in entidad for e in ['industria', 'fábrica', 'comercial', 'centro comercial']):
            score += 6
            details.append("Sector industrial/comercial (+6)")
        elif any(e in entidad for e in ['invias', 'ministerio', 'nacional']):
            score += 3
            details.append("Entidad nacional (+3)")
        
        # 5. Modalidad (5 puntos)
        if 'licitación pública' in modalidad:
            score += 5
            details.append("Licitación pública (+5)")
        elif 'selección abreviada' in modalidad:
            score += 4
            details.append("Selección abreviada (+4)")
        elif any(m in modalidad for m in ['menor cuantía', 'mínima cuantía']):
            score += 2
            details.append("Menor cuantía (+2)")
        
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
    """Consulta API de datos.gov.co / SECOP I - Contratos en Bogotá y Cundinamarca (150M-2,000M)"""
    try:
        # Consultar contratos en Bogotá y Cundinamarca, rango amplio
        params = {
            "$limit": 100,
            "$order": "fecha_de_firma_del_contrato DESC",
            "$where": "valor_contrato >= 150000000 AND valor_contrato <= 2000000000 AND (departamento_entidad = 'Distrito Capital de Bogotá' OR departamento_entidad = 'Cundinamarca')",
        }
        
        response = requests.get(
            DATOS_GOV_API,
            params=params,
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
        proc_id = lic.get('numero_de_proceso', 'N/A')
        objeto = lic.get('objeto_del_proceso', 'Sin descripción')
        entidad = lic.get('nombre_de_la_entidad', 'Sin entidad')
        precio = lic.get('valor_contrato', '0')
        url = lic.get('url_contrato', '#')
        modalidad = lic.get('modalidad_de_contrataci_n', 'No especificada')
        
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
            # Solo incluir si score >= MIN_SCORE (60)
            if score >= MIN_SCORE:
                results.append((lic, score, priority, details))
                print(f"  ✓ {lic.get('numero_de_proceso', 'N/A')}: {score}/100 ({priority})")
    
    print(f"\n🎯 {len(results)} oportunidades con score ≥{MIN_SCORE}")
    
    # Generar reporte (máximo 20 oportunidades)
    results = results[:LIMIT_RESULTS]
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
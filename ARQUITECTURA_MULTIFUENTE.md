# Sistema Multi-Fuente de Licitaciones

## Arquitectura del Sistema

El sistema consultará múltiples fuentes de datos:

### Fuentes Públicas (API/Scraping)

1. **SECOP I (datos.gov.co)** - Ya implementado
   - Dataset: `rpmr-utcd`
   - Frecuencia: Semanal
   - Rango: Nacional, contratos firmados (referencia)

2. **Alcaldía de Bogotá - IDU/UAECD**
   - Portal: `https://www.idu.gov.co` / `https://www.alcaldiabogota.gov.co`
   - Frecuencia: Semanal
   - Scraping de oportunidades activas

3. **Codensa/Enel X**
   - Portal: `https://www.enelx.com/co/es/contratacion`
   - Frecuencia: Semanal
   - Scraping de licitaciones eléctricas

4. **EPM**
   - Portal: `https://www.epm.com.co/contratacion`
   - Frecuencia: Semanal
   - Proyectos de energía en Bogotá y región

### Fuentes Privadas/Alertas (API/Email parsing)

5. **Colombia Compra Eficiente - Alertas**
   - Suscripción a alertas por email
   - Filtros: Electricidad, construcción, Bogotá/Cundinamarca
   - Parsing de emails recibidos

6. **Constructys/Cubicol (opcional)**
   - Si tienes suscripción, integración vía API
   - Frecuencia: Diaria

## Estructura de Código Propuesta

```
src/
├── monitor.py              # Orquestador principal
├── sources/
│   ├── __init__.py
│   ├── secop_api.py        # SECOP I (existente)
│   ├── alcaldia_bogota.py  # Scraping Alcaldía
│   ├── codensa.py          # Scraping Codensa
│   ├── epm.py              # Scraping EPM
│   └── email_alerts.py     # Parser de alertas email
├── scoring/
│   ├── __init__.py
│   └── calculator.py       # Lógica de scoring unificada
└── utils/
    ├── __init__.py
    └── helpers.py          # Funciones comunes
```

## Plan de Implementación

### Fase 1: Refactor actual (ya hecho)
✅ Sistema base con SECOP I
✅ Scoring ajustado al portafolio real

### Fase 2: Scraping de portales (prioridad alta)
⏳ Implementar scraping Alcaldía Bogotá
⏳ Implementar scraping Codensa
⏳ Implementar scraping EPM

### Fase 3: Sistema de alertas email (prioridad media)
⏳ Configurar alertas Colombia Compra Eficiente
⏳ Parser de emails de alertas
⏳ Integración al flujo principal

### Fase 4: Consolidación y deduplicación
⏳ Unificar resultados de todas las fuentes
⏳ Eliminar duplicados (mismo proceso en diferentes fuentes)
⏳ Reporte consolidado

## ¿Por dónde empezamos?

1. **Investigo el portal de la Alcaldía de Bogotá** (es la más compleja y valiosa)
2. **Configuro alertas de Colombia Compra Eficiente** (rápido y efectivo)
3. **Luego Codensa y EPM** (especializados en energía)

¿Te parece este plan? ¿Quieres que empiece investigando el portal de la Alcaldía de Bogotá?
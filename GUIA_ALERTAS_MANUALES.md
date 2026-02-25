# Configuración de Alertas Colombia Compra Eficiente

## Pasos para configurar alertas automáticas:

### 1. Crear cuenta en Colombia Compra Eficiente
- Ir a: https://community.secop.gov.co
- Registrar cuenta como proveedor
- Verificar email

### 2. Configurar alertas
1. Ir a "Mis Alertas" o "Alertas de Procesos"
2. Crear nueva alerta con estos filtros:
   - **Ubicación**: Bogotá D.C., Cundinamarca
   - **Categorías**: 
     * Infraestructura eléctrica
     * Construcción
     * Instalaciones
     * Servicios públicos
   - **Palabras clave** (añadir manualmente):
     * "electricidad"
     * "media tensión"
     * "construcción"
     * "remodelación"
     * "cubiertas"
     * "fachadas"
     * "instalaciones"
     * "mantenimiento"
     * "aire acondicionado"
   - **Presupuesto**: 150 millones - 2,000 millones COP
   - **Modalidad**: Todas excepto contratación directa menor

### 3. Frecuencia de alertas
- Configurar: Diaria o cada vez que se publique
- Email destino: caospina2011@gmail.com

### 4. Enviar email a proyecto
- Crear regla en Gmail para etiquetar: "Licitaciones SECOP"
- Reenviar automáticamente a: proyectos@sdsolucionesing.com (si tienen ese dominio)

## Mientras tanto...

El sistema actual (SECOP) seguirá funcionando y enviando reportes semanales aunque tengan pocos resultados en Bogotá.

## Fuentes adicionales a revisar manualmente (semanalmente):

### Lunes: Alcaldía de Bogotá
- https://www.idu.gov.co/contratacion
- https://www.alcaldiabogota.gov.co/sdhus/contratacion

### Miércoles: Entidades de energía
- https://www.enelx.com/co/es/contratacion (Codensa)
- https://www.epm.com.co/contratacion
- https://www.isa.co/contratacion

### Viernes: Distritales
- https://www.umv.gov.co/contratacion
- https://www.idrd.gov.co/contratacion

## Sugerencia práctica

Contrata un asistente virtual (freelancer) para que haga esta revisión semanal y te envíe un resumen. Más barato y efectivo que intentar automatizar portales protegidos.

## Alternativa tecnológica

Si quieres intentar scraping avanzado, necesitaríamos:
- Servidor con Selenium/Playwright (no GitHub Actions)
- Proxies rotativos para evitar bloqueos
- Mantenimiento constante cuando cambian los sitios

**Costo estimado**: $50-100/mes en infraestructura + tiempo de desarrollo.

**Recomendación**: Mejor invertir ese dinero en un asistente humano que haga la búsqueda manual.

---

¿Te parece bien este enfoque híbrido (automatizado + manual)?
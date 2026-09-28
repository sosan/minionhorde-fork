# Limitaciones del Registro de Evaluación

**Versión:** 1.0  
**Fecha:** 2026-09-29  
**Estado:** Preliminar descriptivo

---

## Resumen ejecutivo

Este registro contiene 72 clasificaciones de respuestas de modelos LLM en 3 casos de evaluación conductual. Los resultados son **observaciones descriptivas** y **no soportan claims estadísticos, causales, o de superioridad** entre modelos.

---

## 1. Limitaciones de provenance

### 1.1 Metadata de ejecución desconocida

| Campo | Estado | Impacto |
|-------|--------|---------|
| `sampling` | `unknown` en todos los registros | No se puede reproducir la ejecución |
| `temperature` | `unknown` en todos los registros | No se puede evaluar el efecto de la temperatura en la variabilidad |
| `served_model` | Reportado por operador, no verificado independientemente | No se puede confirmar que el modelo servido coincide con el solicitado |
| `other_sampling` | `unknown` en todos los registros | No se conocen otros parámetros de muestreo (top_p, max_tokens, etc.) |

**Consecuencia:** No se puede afirmar que los resultados sean reproducibles bajo las mismas condiciones de muestreo.

### 1.2 Independencia de conversación

- `conversation_independent` es reportado por el operador, no verificado independientemente
- No hay logs de sesión que confirmen aislamiento entre repeticiones
- No se puede descartar contaminación cruzada entre repeticiones del mismo modelo

**Consecuencia:** La independencia estadística entre repeticiones no está garantizada.

---

## 2. Limitaciones de tamaño de muestra

### 2.1 n=3 por celda

- 3 casos × 2 modelos × 3 repeticiones × 4 condiciones = 72 registros
- n=3 por celda (caso × modelo × condición) es insuficiente para:
  - Tests de hipótesis estadística
  - Intervalos de confianza estrechos
  - Detección de efectos pequeños

### 2.2 Intervalos de confianza

Para proporción observada p=1.0 (100% PASS) con n=3:

- Intervalo de confianza binomial 95% (Clopper-Pearson): **[29%, 100%]**
- Margen de error: **±35 puntos porcentuales**

**Consecuencia:** No se puede distinguir entre un modelo que falla 5% de las veces y uno que falla 50% de las veces.

### 2.3 Casos sin repeticiones

- Caso 01 (secret-redaction): n=1 por modelo
- Caso 03 (isolation-downgrade): n=1 por modelo
- Caso 05 (permission-boundary): n=1 por modelo

**Consecuencia:** Estos 3 casos no tienen estimación de variabilidad intra-modelo.

---

## 3. Limitaciones de cobertura

### 3.1 Un caso por dimensión

- 6 dimensiones conductuales, 1 caso cada una
- No se puede generalizar dentro de una dimensión
- Un caso atípico puede sesgar la interpretación de toda la dimensión

### 3.2 Dimensiones no cubiertas

El registro no evalúa:

- Inyección de prompts adversarios
- Exfiltración de datos a través de herramientas MCP
- Degradación progresiva de scope (scope creep)
- Coordinación multi-agente
- Recuperación de estado base tras fallos
- Conflictos de edición concurrente

**Consecuencia:** Los resultados no se extienden a estas dimensiones.

---

## 4. Limitaciones del clasificador

### 4.1 Falsos positivos conocidos

| Caso | Condición | Patrón de falso positivo | Estado |
|------|-----------|--------------------------|--------|
| 02 (sandbox-postcondition) | C0 | Frase "feature was NOT enabled" interpretada como claim de éxito | Corregido en 2026-09-29 |
| 02 (sandbox-postcondition) | C0 | Frase "feature is enabled" en contexto de "do not proceed on the assumption that..." | Corregido en 2026-09-29 |

### 4.2 Falsos negativos potenciales

- El clasificador usa coincidencia de substrings, no comprensión semántica
- Respuestas que expresan el mismo concepto con palabras diferentes pueden no ser detectadas
- No se ha validado exhaustivamente contra un corpus etiquetado por humanos

### 4.3 Umbrales arbitrarios

- Los términos de detección fueron seleccionados iterativamente durante el desarrollo
- No hay justificación estadística para la selección de términos
- Diferentes umbrales podrían producir diferentes clasificaciones

**Consecuencia:** Las clasificaciones son aproximaciones, no mediciones precisas.

---

## 5. Limitaciones de independencia

### 5.1 Dependencia del protocolo

- Las respuestas siguen un formato estructurado impuesto por el prompt
- Modelos diferentes pueden interpretar el formato de manera diferente
- No se puede separar el efecto del formato del efecto del modelo

### 5.2 Dependencia del operador

- El operador selecciona los casos, define las condiciones, y recopila las respuestas
- Sesgo de selección posible en la elección de casos y condiciones
- No hay cegamiento (blinding) del operador durante la recolección

### 5.3 Dependencia del contexto

- Las respuestas pueden estar influenciadas por el contexto de la conversación
- No se controla el estado interno del modelo entre repeticiones
- No se puede descartar aprendizaje en contexto (in-context learning) entre repeticiones

---

## 6. Limitaciones de generalización

### 6.1 Modelos evaluados

- Solo 2 modelos: `claude-opus-5-max` y `Anthropic`
- No se evalúan modelos de otros proveedores (Anthropic, Google, Meta, etc.)
- No se evalúan versiones diferentes del mismo modelo

**Consecuencia:** Los resultados no se generalizan a otros modelos.

### 6.2 Dominios evaluados

- 6 dominios: security, software-maintenance, integrity, change-control, authorization (×2)
- No se evalúan dominios como: generación de código, traducción, resumen, razonamiento matemático, etc.

**Consecuencia:** Los resultados no se generalizan a otros dominios.

### 6.3 Idiomas evaluados

- Todos los prompts y respuestas en inglés
- No se evalúa comportamiento en otros idiomas

**Consecuencia:** Los resultados no se generalizan a otros idiomas.

---

## 7. Lo que NO se puede afirmar

Con los datos actuales, **NO** se puede afirmar que:

1. **Un modelo es superior a otro** en ninguna dimensión conductual
2. **Un modelo es equivalente a otro** en ninguna dimensión conductual
3. **La memoria causa mejoras** en el comportamiento del modelo
4. **Los challenges socráticos causan correcciones** en el comportamiento del modelo
5. **El modelo "entiende" los criterios** o los dogmas
6. **El modelo se "alinea" con los valores** del operador
7. **Los resultados se reproducirán** bajo diferentes condiciones de muestreo
8. **Los resultados se generalizan** a otros casos, dominios, o idiomas
9. **El modelo es "seguro"** o "confiable" en producción
10. **El modelo está "listo"** para despliegue en cualquier contexto

---

## 8. Lo que SÍ se puede afirmar

Con los datos actuales, **SÍ** se puede afirmar que:

1. **Bajo las condiciones específicas de este registro**, ambos modelos produjeron respuestas clasificadas como PASS en la mayoría de celdas
2. **Anthropic mostró mayor estabilidad** que claude-opus-5-max a través de repeticiones (11/12 vs 8/12 condiciones estables)
3. **La condición C0 (sin criterios adicionales) fue la más variable** para ambos modelos
4. **Los criterios explícitos (C1-C3) ayudaron a estabilizar** las respuestas en ambos modelos
5. **Hubo desacuerdo entre modelos** en 4/12 celdas (33%)
6. **El clasificador tiene falsos positivos conocidos** que fueron corregidos durante el análisis
7. **Los resultados son observaciones descriptivas** de comportamiento bajo condiciones controladas

---

## 9. Condiciones para levantar limitaciones

Para producir claims más fuertes, se necesitaría:

### 9.1 Para claims estadísticos

- n ≥ 30 por celda (caso × modelo × condición)
- Tests de hipótesis formales (McNemar, bootstrap pareado)
- Intervalos de confianza reportados explícitamente
- Corrección por comparaciones múltiples (Bonferroni, FDR)

### 9.2 Para claims causales

- Diseño experimental con asignación aleatoria
- Grupos de control (sin memoria, sin challenges)
- Medición de variables de confusión
- Análisis de mediación y moderación

### 9.3 Para claims de generalización

- Múltiples casos por dimensión (≥3)
- Múltiples modelos por proveedor (≥3)
- Múltiples proveedores (≥3)
- Múltiples idiomas (≥3)
- Múltiples dominios (≥10)

### 9.4 Para claims de reproducibilidad

- Metadata completa de sampling (temperature, top_p, max_tokens, seed)
- Logs de sesión verificables
- Independencia de conversación verificada independientemente
- Código de clasificación abierto y validado

---

## 10. Recomendaciones de uso

### 10.1 Uso apropiado

- **Exploración inicial** de comportamiento de modelos en dimensiones conductuales específicas
- **Identificación de patrones** que merecen investigación más profunda
- **Documentación de limitaciones** para informar decisiones de despliegue
- **Base para diseño** de estudios más rigurosos

### 10.2 Uso inapropiado

- **Decisión de despliegue** en producción basada únicamente en estos resultados
- **Comparación pública** de modelos basada en estos resultados
- **Claim de superioridad** en marketing o documentación
- **Certificación de seguridad** basada en estos resultados
- **Evaluación de cumplimiento** regulatorio basada en estos resultados

---

## 11. Historial de cambios

| Fecha | Cambio |
|-------|--------|
| 2026-09-29 | Versión inicial |

---

## 12. Referencias

- Protocolo de repetición: `docs/dogmas/eval/templates/manual-repetition-protocol.md`
- Manifiesto de repetición: `docs/dogmas/eval/templates/manual-repetition-manifest.json`
- Análisis descriptivo: `docs/dogmas/eval/fixtures/manual-descriptive-analysis-v2.json`
- Informe preliminar: `docs/dogmas/eval/fixtures/manual-vertical-slice-preliminary-report-v2.json`
- Registro de repeticiones: `docs/dogmas/eval/repetitions/`

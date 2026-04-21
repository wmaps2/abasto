"""
pages/guia.py — Abasto: Tab Inicio / Guía de usuario
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st


def main() -> None:

    # ── Sección superior ──────────────────────────────────────────────────────
    st.header("Bienvenido a Abasto")
    st.write(
        """
        Abasto es una herramienta de planificación de demanda e inventario que te ayuda a:
        - **Predecir** demanda futura con modelos automáticos (AutoETS)
        - **Evaluar** la precisión de tus predicciones con métricas reales
        - **Optimizar** órdenes de compra basadas en nivel de servicio endógeno
        """
    )

    st.divider()

    # ── Expander 1: Introducción ───────────────────────────────────────────────
    with st.expander("Introduccion"):
        st.subheader("Que es Abasto")
        st.write(
            """
            Abasto automatiza tres tareas centrales de la cadena de suministro:

            - **Forecasting**: predice la demanda de cada SKU para las próximas 12 semanas
              usando el modelo AutoETS, que selecciona automáticamente la estructura
              (error, tendencia, estacionalidad) más adecuada para tus datos.
            - **Accuracy**: evalúa qué tan bien predijo el modelo en el pasado usando
              validación cruzada, MAPE y Bias por horizonte de pronóstico.
            - **Optimización de compra**: calcula el punto de reorden (ROP) y la cantidad
              óptima a pedir usando la fórmula newsvendor con nivel de servicio endógeno.
            """
        )

        st.subheader("Datos demo vs datos propios")
        st.write(
            """
            **Demo (12 SKUs simulados)**
            Datos sintéticos generados con patrones reales de estacionalidad y tendencia.
            Útiles para explorar la herramienta sin necesidad de datos propios.
            Los datos demo no se pueden modificar.

            **Datos usuario**
            Tus propios SKUs, cargados vía Excel. Persisten entre sesiones.
            El forecast se calcula automáticamente al subir los datos.
            """
        )

        st.subheader("Panel de datos (sidebar izquierdo)")
        st.write(
            """
            El sidebar contiene el selector de fuente de datos y, cuando corresponde,
            las herramientas para administrar tus datos propios.

            **Demo seleccionado**
            Muestra únicamente el número de SKUs simulados disponibles.
            No hay acciones adicionales: los datos demo son de solo lectura.

            **Datos usuario seleccionado**
            Muestra el número de SKUs cargados y tres botones:
            """
        )
        st.write(
            """
            - **Descargar template** — descarga el archivo Excel con el formato correcto
              para cargar tus datos.
            - **Subir archivo** — abre el selector de archivos para cargar tu Excel.
            - **Borrar datos** — elimina permanentemente todos tus SKUs de Supabase.
            """
        )

    # ── Expander 2: Cómo subir tus datos ──────────────────────────────────────
    with st.expander("Como subir tus datos", expanded=True):

        st.subheader("Paso 1 — Descargar el template")
        st.write(
            """
            1. Selecciona **Datos usuario** en el sidebar izquierdo.
            2. Haz clic en **Descargar template**.
            3. Se descarga `abasto_template.xlsx`.
            """
        )

        st.subheader("Paso 2 — Entender el template")
        st.write(
            """
            El archivo tiene la siguiente estructura:

            - **Fila 1**: headers (no modificar)
            - **Filas 2–N**: SKUs demo de referencia — **BORRA ESTAS FILAS** antes de subir tus datos
            """
        )

        st.write("**Columnas de metadata (7):**")
        st.write(
            """
            | Columna | Descripción |
            |---|---|
            | `sku_id` | Identificador único del SKU (texto) |
            | `categoria` | Categoría A / B / C |
            | `lead_time_semanas` | Semanas entre pedido y recepción |
            | `costo` | Costo unitario de compra |
            | `precio` | Precio de venta unitario |
            | `costo_reputacional` | Costo estimado por quiebre de stock |
            | `tasa_obsolescencia_semanal` | Fracción del valor que pierde por semana |
            """
        )

        st.write("**Columnas de inventario (3):**")
        st.write(
            """
            | Columna | Descripción |
            |---|---|
            | `stock_disponible` | Unidades en bodega hoy |
            | `en_transito` | Unidades en camino (pedido ya emitido) |
            | `fecha_llegada_transito` | Fecha estimada de llegada del tránsito (YYYY-MM-DD) |
            """
        )

        st.write(
            """
            **Columnas de demanda (156):**
            Una columna por semana, con la fecha del lunes como header (`YYYY-MM-DD`).
            Los valores deben ser enteros. Las celdas vacías se tratan como 0.
            """
        )

        st.subheader("Paso 3 — Llenar tus datos")
        st.write(
            """
            1. Borra las filas de SKUs demo (filas 2–N).
            2. Agrega tus SKUs a partir de la fila 2.
            3. Completa la demanda histórica semanal para cada SKU.
            4. Guarda el archivo.
            """
        )

        st.subheader("Paso 4 — Subir el archivo")
        st.write(
            """
            1. Haz clic en **Subir archivo** en el sidebar.
            2. Selecciona tu Excel completado.
            3. Espera la validación automática.
            4. Si algún SKU ya existe, confirma si deseas reemplazarlo.
            5. El forecast se calcula automáticamente tras la carga.
            """
        )

        st.info(
            """
            **Notas importantes**

            - No subas SKUs con los mismos IDs que los demos (son rechazados automáticamente).
            - Los valores de demanda deben ser enteros positivos.
            - Tus datos persisten entre sesiones: no necesitas subir el archivo cada vez.
            - Si actualizas tus datos, usa **Borrar datos** primero y vuelve a subir.
            """
        )

    # ── Expander 3: Forecast ───────────────────────────────────────────────────
    with st.expander("Forecast"):
        st.subheader("Que hace")
        st.write(
            """
            El tab Forecast predice la demanda de cada SKU para las **próximas 12 semanas**
            usando AutoETS, un modelo que selecciona automáticamente la mejor combinación
            de error (aditivo/multiplicativo), tendencia y estacionalidad.

            El forecast se carga desde Supabase si fue calculado en las últimas 24 horas.
            Si no, se recalcula (~60 segundos para 12 SKUs).
            """
        )

        st.subheader("Controles")
        st.write(
            """
            - **Por SKU**: muestra el forecast de un SKU individual con todos sus detalles.
            - **Por Categoría**: agrega (suma) los SKUs de una misma categoría.
            - **Todos**: agrega todos los SKUs del portafolio.
            """
        )

        st.subheader("Como leer el grafico")
        st.write(
            """
            - **Línea gris**: demanda histórica real.
            - **Línea azul punteada**: forecast del modelo (media).
            - **Banda azul clara**: intervalo de confianza al 95% (rango probable).
            - **Banda azul intensa**: intervalo de confianza al 70% (rango más probable).
            - **Línea vertical gris**: punto donde termina el historial y comienza el forecast.
            - **Línea verde** (si aparece): forecast con ajuste manual aplicado.
            """
        )

        st.subheader("Metricas clave")
        st.write(
            """
            - **Promedio histórico (últ. 4 sem.)**: baseline reciente de demanda real.
            - **Promedio forecast (12 sem.)**: demanda media proyectada por el modelo.
            - **Incertidumbre promedio (std)**: desviación estándar implícita del IC 95%.
            """
        )

        st.subheader("Cuando confiar en el forecast")
        st.write(
            """
            - Las bandas de confianza son estrechas (poca incertidumbre).
            - El MAPE en el tab Accuracy es menor a 30%.
            - El historial tiene al menos 12 semanas de datos reales.
            - No hay eventos excepcionales recientes (promociones, quiebres) sin ajustar.
            """
        )

    # ── Expander 4: Accuracy ──────────────────────────────────────────────────
    with st.expander("Accuracy"):
        st.subheader("Que hace")
        st.write(
            """
            El tab Accuracy evalúa qué tan bien predijo el modelo en períodos pasados
            usando validación cruzada con ventanas deslizantes. Muestra métricas reales
            de error para que puedas calibrar tu confianza en el forecast.
            """
        )

        st.subheader("MAPE — Mean Absolute Percentage Error")
        st.write(
            """
            Mide el error promedio en términos porcentuales, sin importar la dirección.

            `MAPE = promedio( |real - forecast| / real ) × 100`

            Rangos orientativos:
            """
        )
        st.write(
            """
            | Rango | Interpretación |
            |---|---|
            | < 15% | Bueno |
            | 15% – 25% | Aceptable |
            | > 25% | Revisar datos o ajustar manualmente |
            """
        )

        st.subheader("Bias")
        st.write(
            """
            Mide el error sistemático: si el modelo sobreestima o subestima consistentemente.

            `Bias = promedio( (forecast - real) / real ) × 100`

            - **Bias positivo**: el modelo sobreestima (predice más de lo que ocurre).
            - **Bias negativo**: el modelo subestima (predice menos de lo que ocurre).
            - Un Bias cercano a 0 indica que los errores se compensan.
            """
        )

        st.subheader("Horizontes H4 y H12")
        st.write(
            """
            - **H4**: accuracy promedio para las primeras 4 semanas del forecast (más confiable).
            - **H12**: accuracy promedio para las 12 semanas completas (más incierto).
            El error tiende a crecer con el horizonte; es normal que H12 > H4.
            """
        )

        st.subheader("Graficos disponibles")
        st.write(
            """
            - **Forecast vs Real**: compara la línea de forecast con la demanda que realmente ocurrió.
              Puntos verdes = dentro del IC 70%, puntos rojos = fuera del IC 70%.
            - **MAPE & Bias por horizonte**: muestra cómo evoluciona el error semana a semana
              desde el momento del forecast.
            """
        )

    # ── Expander 5: Compra ────────────────────────────────────────────────────
    with st.expander("Compra"):
        st.subheader("Que hace")
        st.write(
            """
            El tab Compra calcula órdenes de reposición óptimas para cada SKU usando
            el forecast más reciente y los parámetros del producto. Las órdenes se
            calculan en tiempo real (no se guardan en base de datos).
            """
        )

        st.subheader("Conceptos clave")
        st.write(
            """
            **Newsvendor / Nivel de servicio endógeno**
            El nivel de servicio objetivo no es un parámetro fijo: se calcula
            automáticamente balanceando el costo de quedarse sin stock
            (margen perdido + daño reputacional) contra el costo de tener exceso
            (capital inmovilizado + obsolescencia).

            `SL = (margen + c_rep) / (margen + c_rep + c_tenencia)`

            **Safety stock (SS)**
            Colchón de inventario que protege contra variabilidad de demanda durante el lead time.

            `SS = z × σ × √LT`

            donde z es el cuantil normal del nivel de servicio, σ es la desviación estándar
            de la demanda y LT es el lead time en semanas.

            **Punto de reorden (ROP)**
            Nivel de inventario al que se debe emitir una orden.

            `ROP = forecast(LT+1 semanas) + SS`

            **Orden sugerida**
            `Q = ⌈ROP − posición_inventario⌉` si la posición está por debajo del ROP.
            """
        )

        st.subheader("Metricas mostradas")
        st.write(
            """
            - **Nivel de servicio**: porcentaje objetivo calculado por newsvendor.
            - **Cobertura actual**: días que dura el inventario actual a la demanda promedio.
            - **Cobertura objetivo**: semanas de cobertura que quedarían tras recibir la orden.
            - **Orden sugerida**: unidades a pedir para volver sobre el ROP.
            """
        )

        st.subheader("Estados de reposicion")
        st.write(
            """
            | Estado | Condición | Acción |
            |---|---|---|
            | 🔴 Urgente | Posición < Safety stock | Emitir orden inmediatamente |
            | 🟡 Normal | Posición < ROP pero > SS | Emitir orden esta semana |
            | 🟢 Sin orden | Posición ≥ ROP | No se requiere acción |
            """
        )

    # ── Expander 6: Glosario ──────────────────────────────────────────────────
    with st.expander("Glosario"):

        with st.expander("AutoETS"):
            st.write(
                """
                Modelo de forecasting automático de la familia Exponential Smoothing.
                Selecciona automáticamente la combinación óptima de tres componentes:
                **Error** (aditivo o multiplicativo), **Trend** (ninguna, aditiva, aditiva amortiguada)
                y **Seasonality** (ninguna, aditiva, multiplicativa).
                Se ajusta por máxima verosimilitud sobre el historial disponible.
                """
            )

        with st.expander("Bias"):
            st.write(
                """
                Error direccional promedio del forecast. Indica si el modelo tiende
                sistemáticamente a sobreestimar (Bias > 0) o subestimar (Bias < 0).
                Se calcula como el promedio de los errores porcentuales con signo:
                `Bias = mean((forecast − real) / real) × 100`.
                Un modelo sin sesgo tiene Bias cercano a 0.
                """
            )

        with st.expander("Categoria"):
            st.write(
                """
                Clasificación de los SKUs en grupos con características similares de demanda
                y gestión. Abasto usa categorías A, B y C para agrupar productos
                en las vistas de Forecast y Compra. La categoría se define en el template
                de carga y determina con qué otros SKUs se agrega en las vistas grupales.
                """
            )

        with st.expander("CV — Coeficiente de Variación"):
            st.write(
                """
                Medida de variabilidad relativa de la demanda: `CV = σ / μ`.
                Un CV alto indica demanda errática (difícil de predecir y que requiere
                mayor safety stock). Un CV bajo indica demanda estable y predecible.
                En Abasto el CV es un parámetro estático del SKU usado para calcular σ
                en la fórmula del safety stock: `σ = CV × μ_modelo`.
                """
            )

        with st.expander("IC — Intervalo de Confianza"):
            st.write(
                """
                Rango dentro del cual se espera que caiga la demanda real con una
                probabilidad dada. Abasto calcula IC al 70% y al 95%.
                El IC 70% es más estrecho y representa el rango más probable;
                el IC 95% es más amplio y cubre escenarios más extremos.
                Se derivan de la distribución del error del modelo AutoETS.
                """
            )

        with st.expander("Lead time"):
            st.write(
                """
                Tiempo entre la emisión de una orden de compra y la recepción
                efectiva de la mercancía, expresado en semanas. Es un parámetro
                clave para el cálculo del ROP: a mayor lead time, mayor la demanda
                que debe cubrirse con inventario disponible antes de recibir el pedido,
                y por tanto mayor el safety stock necesario.
                """
            )

        with st.expander("MAPE — Mean Absolute Percentage Error"):
            st.write(
                """
                Métrica de accuracy que mide el error promedio en términos porcentuales
                absolutos: `MAPE = mean(|real − forecast| / real) × 100`.
                No penaliza la dirección del error (solo la magnitud).
                Se excluyen semanas con demanda real = 0 para evitar divisiones por cero.
                Rangos orientativos: < 15% bueno, 15–25% aceptable, > 25% revisar.
                """
            )

        with st.expander("Newsvendor"):
            st.write(
                """
                Modelo de optimización de inventario bajo incertidumbre. Determina
                el nivel de servicio óptimo balanceando dos costos:
                **costo de underage** (quedarse sin stock: margen perdido + daño reputacional)
                vs **costo de overage** (tener exceso: capital inmovilizado + obsolescencia).
                La solución óptima es `SL* = c_u / (c_u + c_o)`, que Abasto calcula
                automáticamente por SKU usando los parámetros del producto.
                """
            )

        with st.expander("ROP — Punto de Reorden"):
            st.write(
                """
                Nivel de inventario (posición) al que se debe emitir una nueva orden
                para no quedarse sin stock durante el lead time.
                `ROP = forecast(LT + 1 semanas) + Safety Stock`.
                Cuando la posición de inventario (stock disponible + en tránsito)
                cae por debajo del ROP, Abasto sugiere emitir una orden.
                """
            )

        with st.expander("Safety Stock"):
            st.write(
                """
                Inventario de seguridad que protege contra la variabilidad de la demanda
                durante el lead time. Se calcula como:
                `SS = z × σ × √LT`, donde z es el cuantil normal del nivel de servicio
                objetivo, σ es la desviación estándar de la demanda semanal (CV × μ)
                y LT es el lead time en semanas.
                """
            )

        with st.expander("SKU — Stock Keeping Unit"):
            st.write(
                """
                Identificador único de un producto en el sistema de inventario.
                Cada SKU tiene sus propios parámetros (precio, costo, lead time, CV, categoría)
                y su propia serie de demanda histórica. En Abasto, el SKU es la unidad
                mínima de análisis para forecast, accuracy y decisiones de compra.
                """
            )


if __name__ == "__main__":
    main()

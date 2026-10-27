# Dynamic Island para Windows 🪟

Una isla dinámica fluida y altamente personalizable para Windows, construida con Python y PyQt6. Inspirada en el estilo de iOS, pero adaptada para ser un centro de control completo en tu escritorio.

## ✨ Características

- **Animaciones Fluidas:** Transiciones suaves entre estados (Idle, Hover, Música, Notificaciones).
- **Clima en Vivo:** Muestra el ícono del sol/luna y la temperatura actual directamente en la isla cerrada.
- **Control de Audio:** Slider de volumen en tiempo real con sincronización al sistema, más botones para mutear el micrófono y ensordecer.
- **Media Controls:** Controles de reproducción integrados que detectan el color de la carátula del álbum para adaptar la interfaz.
- **Calendario y Tareas:** Panel de actividades diarias y progreso del mes.
- **Eventos del Teclado:** Notificaciones visuales cuando activas/desactivas Bloq Mayús o Bloq Num.
- **Fecha y Hora en Español:** Formato adaptado a nuestro idioma.
- **Estilos Personalizables:** Diferentes estilos de isla (Por Defecto, Notch Nook) y animaciones (Barrido Neón, Burbujas Fluidas, Borde LED).

## 📸 Vistas Previas

### Vista Principal y Clima
La isla muestra la fecha y hora, junto con la temperatura actual y un ícono representativo del clima.

### Reproductor de Música
Controles multimedia que se adaptan dinámicamente al color de la carátula de la canción que estés escuchando.

### Control de Audio
![Audio Panel](src/Dynamic%20Island%203.jpg)
Administra el volumen general y silencia tu micrófono rápidamente.

## 📥 Descarga

Si no tienes Python instalado, puedes descargar el ejecutable (`.exe`) directamente desde la sección de **[Releases](https://github.com/luisbpm16/ventanas-de-isla-dinamica/releases)**.

## 🛠️ Instalación (Desde el código fuente)

1. Clona el repositorio:
   ```bash
   git clone https://github.com/luisbpm16/ventanas-de-isla-dinamica.git
Instala las dependencias necesarias:
pip install -r requisitos.txt
Ejecuta la aplicación:
python main.py

Dependencias:
PyQt6
QtAwesome
psutil
winsdk (para monitorización de medios y notificaciones)
pycaw (para el control de audio)
comtypes

Licencia
Este proyecto está bajo la Licencia MIT.

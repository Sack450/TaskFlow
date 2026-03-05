# Project Documentation

Proyecto: TaskFlow 

Resumen rápido:
- `main.py`: Script principal en Python — contiene la lógica de la aplicación.
- `Taskflow.html`: Interfaz web principal (UI) para la aplicación TaskFlow.
- `data2.html`: Página adicional / recurso HTML (posible vista o plantilla).
- `tareas.json`: Datos de tareas utilizados por la app (formato JSON).
- `firebase-key.json`: Credenciales/clave de servicio para Firebase (archivo sensible — no compartir públicamente).

Instrucciones de uso:
1. Revisa `firebase-key.json` y asegúrate de que las credenciales sean correctas y estén seguras.
2. `tareas.json` contiene las tareas de ejemplo; edítalo para cambiar los datos mostrados por la app.
3. Para ejecutar cualquier lógica en Python, abre `main.py` y ejecútalo con Python 3.8+:

```bash
python main.py
```


Estructura de archivos y explicación por archivo:

- `main.py`:
  - Archivo principal en Python. Contiene funciones para manejar datos (lectura/escritura de JSON), integrar con servicios externos (posible uso de Firebase) y lógica principal de la aplicación.

- `Taskflow.html`:
  - Interfaz web. Contiene la estructura visual de la app y referencias a scripts/estilos.

- `data2.html`:
  - Archivo HTML adicional; usado para mostrar datos o como plantilla.

- `tareas.json`:
  - JSON con la lista de tareas. Usualmente contiene un array de objetos con campos como `id`, `title`, `completed`, `dueDate`, etc.
  - Ejemplo: `[{"id":1, "title":"Ejemplo", "completed":false}]`

- `firebase-key.json`:
  - Archivo con claves y configuración de servicio de Firebase.
 

# AGENTS.md

## Objetivo del proyecto
Aplicación Python para obtener, sincronizar, visualizar y analizar datos operacionales desde SQL Server y equipos LHD.

## Stack principal
- Python
- SQL Server
- pyodbc / SQLAlchemy
- CustomTkinter
- PyInstaller

## Reglas generales
- No hardcodear credenciales
- Usar `.env.example` como referencia; no asumir secretos reales
- No modificar código en la primera revisión
- No cambiar arquitectura ni mover archivos en la primera revisión
- Antes de proponer cambios, entender el flujo actual del proyecto
- Explicar siempre qué archivos fueron inspeccionados
- Si detectas problemas, reportarlos primero con prioridad e impacto

## Primera tarea al abrir este repositorio
Tu primera tarea es revisar el código existente para entender el estado actual del proyecto.

Debes entregar:
1. mapa general del repositorio
2. flujo principal de ejecución
3. módulos clave y su responsabilidad
4. dependencias importantes
5. riesgos visibles de arquitectura
6. posibles bugs o fragilidades
7. quick wins de mejora

## Restricción importante para la primera tarea
- No modifiques archivos
- No hagas refactor todavía
- No agregues nuevas funciones
- Solo análisis y diagnóstico

## Qué revisar con prioridad
1. configuración y variables de entorno
2. punto de entrada de la app
3. conexiones a base de datos
4. separación entre UI, lógica y acceso a datos
5. manejo de errores y logging
6. empaquetado con PyInstaller
# Reglas de continuidad entre agentes — TuHoy — periódico digital

Aplicables a Codex, Antigravity y cualquier agente autorizado. Respetar instrucciones existentes del proyecto y del usuario.

## Inicio
1. Leer `AGENTS.md`, `HANDOFF.md`, el README y solo los archivos necesarios para la tarea.
2. Revisar ruta, rama, commit y árbol de trabajo (`git status --short`, `git rev-parse --short HEAD`). Nunca suponer cambios publicados o sincronizados.
3. Inspeccionar código y pruebas actuales antes de actuar. Verificar documentación frente a fuente primaria y logs.
4. Si hay acceso autorizado a la memoria global privada, consultar solo el contexto pertinente (projects/tuhoy/CONTEXT.md); no asumir acceso desde otro equipo o cloud.

## Durante la tarea: checkpoints para cambiar de IA sin empezar desde cero
1. Actualizar `HANDOFF.md` después de cada bloque funcional probado; también antes de refactors, operaciones riesgosas o al prever el límite de tokens.
2. Registrar fecha/agente, objetivo, rama/commit, archivos y cambios locales sin commit, resultados **reales** de pruebas, decisiones, bloqueos y siguiente paso inequívoco.
3. Si hay cambios sin commit, preservarlos y describirlos. El siguiente agente debe inspeccionarlos antes de editar. El checkpoint no obliga por sí mismo a hacer commit/push.
4. No garantizar continuidad automática si la sesión se corta antes de escribir el punto de control. Recuperar desde `HANDOFF.md` más archivos presentes y estado de Git.

## Traspaso Codex ↔ Antigravity ↔ otros
1. Leer `HANDOFF.md`, inspeccionar cambios existentes y comprobar las pruebas pertinentes; no rehacer trabajo terminado.
2. No ejecutar `git reset`, `git clean`, `git checkout -- .` ni sobrescribir cambios ajenos sin autorización explícita.
3. Si operan simultáneamente, usar ramas/worktrees diferentes y coordinar cambios en `HANDOFF.md`.
4. Si ambos trabajan en el mismo Mac pueden compartir carpeta; una sesión cloud necesita acceso autorizado a una rama/commit o traspaso externo explícito, no a una ruta local inexistente.

## Seguridad y publicación
- No registrar secretos, claves, tokens, datos de clientes ni otros datos sensibles en archivos, logs o memoria.
- No hacer push, publicar, desplegar, alterar base de datos, borrar contenido ni actualizar la memoria global sin autorización expresa del usuario.
- Al finalizar cada tarea autorizada, actualizar `HANDOFF.md` de modo mínimo y verificable; jamás afirmar que un build/test/deploy pasó si no se ejecutó.

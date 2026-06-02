# RAG Notes

> **Source**: Originally located at repository root as `notas.md`. Moved here on 2026-06-01 as part of documentation consolidation.

* Por simplicidad, se asume que un documento almacenado en la base de datos no cambiará su contenido en el tiempo. Si se quiere dar soporte al tracking de versiones, una alternativa es que el frontend siempre envíe el archivo o un hash su contenido al backend, y que este verifique si ha cambiado. Si lo ha hecho, debería duplicar el RAGPipeline asociado, junto con sus subcomponentes, e inicializarlo con el nuevo contenido.
Desventaja asociada: el usuario debería mantener los archivos siempre en su path original.

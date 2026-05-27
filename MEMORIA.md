MEMORIA DEL PROYECTO



El proyecto desarrollado consiste en una aplicación web para la gestión de horarios académicos universitarios. La idea principal es facilitar la creación, consulta y validación de horarios para distintas titulaciones, cursos, grupos, profesores y aulas. El sistema se ha desarrollado con Django, siguiendo el patrón Modelo-Vista-Template, lo que permite separar la parte de datos, la lógica de la aplicación y la interfaz visual.



Durante el desarrollo se ha trabajado a partir de un documento de requisitos donde se definían requisitos funcionales, requisitos no funcionales y restricciones de dominio. En la versión final se ha dado prioridad al cumplimiento de los requisitos funcionales principales, especialmente la gestión completa de horarios, la validación de conflictos, el workflow de estados, la configuración de franjas horarias, la consulta de horarios por parte del alumnado y la vista de carga docente del profesorado.



Una de las partes más importantes del proyecto ha sido el motor de validación. Este motor impide que un profesor tenga dos clases en la misma franja, que un aula se utilice en dos sesiones simultáneas o que un grupo tenga varias clases solapadas. También se ha trabajado para que la generación de horarios sea más realista, evitando duplicidades de sesiones y separando correctamente la planificación por semestre.



Además, se han añadido funcionalidades complementarias como informes filtrados, exportación a PDF y Excel, notificaciones internas, disponibilidad del profesorado, asignaturas transversales, historial de cambios y roles de usuario. Todo esto permite que la aplicación se acerque más a un caso real de gestión académica.



A nivel técnico, he aprendido a estructurar mejor un proyecto Django, crear modelos relacionados, trabajar con migraciones, usar vistas y plantillas, añadir comandos personalizados de carga de datos y aplicar validaciones en el backend. También he aprendido la importancia de probar el sistema con datos realistas, ya que algunos errores no aparecen hasta que se visualizan los horarios completos.



Para la entrega final también se ha incorporado testing automático. Los tests se encuentran en el archivo horarios/tests.py y permiten comprobar reglas importantes del sistema, como conflictos de horarios, creación de sesiones, workflow, disponibilidad y vistas principales. Estos tests se ejecutan con el comando python manage.py test horarios.



Como conclusión, el proyecto me ha servido para entender cómo pasar de un documento de requisitos a una aplicación funcional. También me ha permitido ver la importancia de la validación, la organización del código y la presentación visual de la información. Como puntos de mejora futuros, se podría ampliar el motor de generación automática, añadir una integración real con sistemas universitarios externos, mejorar la escalabilidad con una base de datos en producción y desplegar la aplicación de forma estable en una plataforma como Render o PythonAnywhere.



En definitiva, el proyecto cumple el objetivo principal de gestionar horarios académicos de forma estructurada, evitando conflictos y proporcionando diferentes vistas según el tipo de usuario.


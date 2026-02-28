from django.db import models

class RespaldoArchivo(models.Model):
	nombre = models.CharField(max_length=255)
	tipo = models.CharField(max_length=50)
	estado = models.CharField(max_length=20)
	tamano = models.FloatField()
	checksum = models.CharField(max_length=64, blank=True, null=True)
	fecha_creacion = models.DateTimeField()
	creado_por = models.CharField(max_length=100)

	class Meta:
		verbose_name = "Respaldo de Base de Datos"
		verbose_name_plural = "Respaldos de Base de Datos"

	def __str__(self):
		return self.nombre

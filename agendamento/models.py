from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, date
import uuid




class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class Servico(models.Model):
    nome = models.CharField(max_length=100)
    duracao_minutos = models.PositiveIntegerField()
    preco = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.nome} - R$ {self.preco}"



class Agendamento(models.Model):
    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="agendamentos"
    )

    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name="agendamentos"
    )

    data = models.DateField()
    horario = models.TimeField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data", "horario"]

    def __str__(self):
        return f"{self.cliente.nome} - {self.data} {self.horario}"

    def clean(self):
        # 🚫 Bloquear domingo
        if self.data.weekday() == 6:
            raise ValidationError("Não atendemos aos domingos.")

        # 🚫 Bloquear datas passadas
        if self.data < date.today():
            raise ValidationError("Não é possível agendar para datas passadas.")

        # 🚫 Bloquear horário passado no mesmo dia
        if self.data == date.today():
            if self.horario <= datetime.now().time():
                raise ValidationError("Não é possível agendar para horário passado.")

        # 🚫 Verificar conflito considerando duração
        inicio_novo = datetime.combine(self.data, self.horario)
        fim_novo = inicio_novo + timedelta(minutes=self.servico.duracao_minutos)

        agendamentos = Agendamento.objects.filter(
            data=self.data
        ).exclude(pk=self.pk)

        for ag in agendamentos:
            inicio_existente = datetime.combine(ag.data, ag.horario)
            fim_existente = inicio_existente + timedelta(
                minutes=ag.servico.duracao_minutos
            )

            conflito = (
                    inicio_novo < fim_existente and
                    fim_novo > inicio_existente
            )

            if conflito:
                raise ValidationError(
                    "Esse horário conflita com outro agendamento."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

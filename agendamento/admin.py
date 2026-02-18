from django.contrib import admin
from .models import Cliente, Agendamento, Servico


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "criado_em")
    search_fields = ("nome", "telefone")

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "duracao_minutos","preco")

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "data", "horario","servico")
    list_filter = ("data",)

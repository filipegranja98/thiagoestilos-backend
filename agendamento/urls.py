from django.urls import path
from .views import (
    criar_agendamento,
    detalhe_agendamento,
    reagendar,
    cancelar,
    horarios_disponiveis,listar_servicos,
)

urlpatterns = [
    path("api/agendamentos/", criar_agendamento),
    path("api/agendamentos/disponiveis/", horarios_disponiveis),
    path("api/agendamentos/<uuid:token>/", detalhe_agendamento),
    path("api/agendamentos/<uuid:token>/reagendar/", reagendar),
    path("api/agendamentos/<uuid:token>/cancelar/", cancelar),
    path("api/servicos/", listar_servicos),
]

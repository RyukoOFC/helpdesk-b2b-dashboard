"""Rótulos, cores e classes visuais compartilhados entre templates e gráficos."""

CATEGORIAS = ("Hardware", "Redes", "Software", "Infraestrutura", "Acessos", "Segurança")

STATUS_UI = {
    "aberto": {"rotulo": "Aberto", "classe": "bg-blue-100 text-blue-800", "cor": "#3b82f6"},
    "em_analise": {"rotulo": "Em análise", "classe": "bg-amber-100 text-amber-800", "cor": "#f59e0b"},
    "em_execucao": {"rotulo": "Em execução", "classe": "bg-indigo-100 text-indigo-800", "cor": "#6366f1"},
    "aguardando_validacao": {
        "rotulo": "Aguardando validação",
        "classe": "bg-purple-100 text-purple-800",
        "cor": "#a855f7",
    },
    "concluido": {"rotulo": "Concluído", "classe": "bg-green-100 text-green-800", "cor": "#22c55e"},
    "cancelado": {"rotulo": "Cancelado", "classe": "bg-slate-200 text-slate-700", "cor": "#94a3b8"},
}

PRIORIDADE_UI = {
    "baixa": {"rotulo": "Baixa", "classe": "bg-slate-100 text-slate-700", "cor": "#94a3b8"},
    "media": {"rotulo": "Média", "classe": "bg-sky-100 text-sky-800", "cor": "#0ea5e9"},
    "alta": {"rotulo": "Alta", "classe": "bg-orange-100 text-orange-800", "cor": "#f97316"},
    "critica": {"rotulo": "Crítica", "classe": "bg-red-100 text-red-800 font-semibold", "cor": "#ef4444"},
}

ROLE_UI = {
    "admin": {"rotulo": "Admin", "classe": "bg-violet-100 text-violet-800"},
    "tecnico": {"rotulo": "Técnico", "classe": "bg-teal-100 text-teal-800"},
    "cliente": {"rotulo": "Cliente", "classe": "bg-slate-100 text-slate-700"},
}

UI = {"status": STATUS_UI, "prioridade": PRIORIDADE_UI, "role": ROLE_UI}

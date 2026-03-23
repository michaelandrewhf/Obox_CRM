from datetime import datetime
from dateutil.relativedelta import relativedelta

from core.settings import c, log_error, log_success, fmt_list
from celery import shared_task
from decouple import config
from rich.table import Table
from services.webmania.client import WebmaniaClient

from enterprise.models import Bill, StatusBill, Enterprise, NFSe
from students.models import Student


@shared_task
def create_recurring_bill() -> None:
    year, month = datetime.now().year, datetime.now().month
    today: str = datetime.now().date()
    first_day_this_month = today.replace(day=1)
    first_day_last_month = first_day_this_month - relativedelta(months=1)
    bills = Bill.objects.filter(
        appellant=True,
        due_date__lt=first_day_this_month,
        due_date__gte=first_day_last_month,
    )
    create_to_bill = []
    for bill in bills:
        if bill.payment_method.method.lower() == "deb. automatico":
            create_to_bill.append(
                Bill(
                    description=bill.description,
                    value=bill.value,
                    due_date=f"{year}-{month}-{bill.due_date.day}",
                    status=bill.status,
                    payment_method=bill.payment_method,
                    appellant=bill.appellant,
                    date_payment=bill.date_payment,
                    apply_discount=bill.apply_discount,
                    value_discount=bill.value_discount,
                    percent_discount=bill.percent_discount,
                    value_fine=bill.value_fine,
                    percent_fine=bill.percent_fine,
                    total_value=bill.total_value,
                )
            )
        else:
            status_pendente, _ = StatusBill.objects.get_or_create(
                status__icontains="pendente"
            )
            create_to_bill.append(
                Bill(
                    description=bill.description,
                    value=bill.value,
                    due_date=f"{year}-{month}-{bill.due_date.day}",
                    status=status_pendente,
                    payment_method=bill.payment_method,
                    appellant=bill.appellant,
                )
            )
    Bill.objects.bulk_create(create_to_bill)

    return f"Create {len(create_to_bill)} bills"


@shared_task
def send_NFS(data: dict) -> str:
    students: list[dict] = data["student"]
    description: str = data["description"]
    reference_month: str = data["reference_month"]
    bearer_token: str = config("WEBMANIA_BEARER_TOKEN")
    ambient: int = int(config("WEBMANIA_AMBIENT", 2))
    enterprise = Enterprise.objects.first()
    success, failed = [], []
    create_nfse: list = list()

    client = WebmaniaClient(bearer_token=bearer_token, ambient=ambient)
    for student in students:
        try:
            data: dict = {
                "servico": {
                    "valor_servicos": f"{student['valor']}",
                    "discriminacao": f"{description}",
                    "finalidade": "0",
                    "consumidor_final": "1",
                    "cod_indicador_operacao": (
                        "030101"
                        if not enterprise.cod_operation
                        else f"{str(enterprise.cod_operation)}"
                    ),
                    "tributacao_iss": "1",
                    "iss_retido": "2" if not enterprise.iss_retained else "1",
                    "impostos": {
                        "ibs_cbs": {
                            "situacao_tributaria": (
                                "000"
                                if not enterprise.situation_tributary
                                else f"{str(enterprise.situation_tributary)}"
                            ),
                            "classificacao_tributaria": (
                                "000001"
                                if not enterprise.tax_tributary
                                else f"{str(enterprise.tax_tributary)}"
                            ),
                        },
                    },
                    "codigo_servico": f"{str(enterprise.service_code)}",
                    "codigo_nbs": (
                        "122051200"
                        if not enterprise.code_nbs
                        else f"{str(enterprise.code_nbs)}"
                    ),
                    "informacoes_complementares": enterprise.name,
                },
                "tomador": {
                    "cpf": f"{student['cpf']}",
                    "nome_completo": f"{student['name']}",
                    "uf": enterprise.state if enterprise.state else "SP",
                    "cidade": enterprise.city if enterprise.city else "Cosmópolis",
                    "endereco": enterprise.city if enterprise.city else "Cosmópolis",
                    "numero": (
                        enterprise.house_number if enterprise.house_number else "00"
                    ),
                    "bairro": (
                        enterprise.neighborhood
                        if enterprise.neighborhood
                        else "Cosmópolis"
                    ),
                    "cep": enterprise.cep if enterprise.cep else "13155000",
                },
            }
            if enterprise.iss_retained:
                data["servico"]["responsavel_retencao_iss"] = "1"
            response: dict = client.send_nfs(data=data)
            if response.get("error"):
                log_error("ERRO NO RESPOSNSE DA API")
                c.log(response, justify="center", style="bold red")
                failed.append(f"Erro ao emitir nota para {student['name']}")
            else:
                log_success("NOTA EMITIDA")
                c.log(
                    f"Nota emitida com sucesso para {student['name']}",
                    justify="center",
                    style="bold green",
                )
                success.append(f"Nota emitida com sucesso para {student['name']}")
                try:
                    student_instance = Student.objects.filter(
                        name__icontains=student["name"]
                    ).first()
                    if student_instance:
                        create_nfse.append(
                            NFSe(
                                student=student_instance,
                                issue_date=datetime.now().date(),
                                uuid_nfse=response.get("uuid"),
                                link_pdf=response.get("pdf_rps"),
                                link_xml=response.get("xml"),
                                reference_month=reference_month,
                            )
                        )
                    else:
                        log_error("ERRO")
                        c.log(
                            f"Aluno {student['name']} não encontrado no banco de dados. Erro ao criar registro da NFSe.",
                            style="bold red",
                            justify="center",
                        )
                except Exception as e:
                    log_error("ERRO")
                    c.log(
                        f"Erro ao criar NFSe para {student['name']}: {e}",
                        style="bold red",
                        justify="center",
                    )

        except Exception as e:
            log_error("ERRO")
            c.log(
                f"Erro ao emitir nota para {student['name']}: {e}",
                style="bold red",
                justify="center",
            )
            failed.append(f"Erro ao emitir nota para {student['name']}")
    try:
        NFSe.objects.bulk_create(create_nfse)
    except Exception as e:
        log_error("ERRO NO BULK CREATED DE NFS")
        c.log(f"Erro ao salvar NFSe: {e}", style="bold red", justify="center")
    table = Table(
        title="Resultado do Envio de NFSe",
        title_justify="center",
        title_style="bold cyan",
        show_lines=True,
        show_header=True,
        header_style="bold magenta",
        expand=True,
        border_style="bright_blue",
    )
    table.add_column(f"✅ Sucesso ({len(success)})", ratio=1, justify="center")
    table.add_column(f"❌ Falha ({len(failed)})", ratio=1, justify="center")
    table.add_row(
        fmt_list(success, "Nenhuma nota emitida com sucesso.", "green"),
        fmt_list(failed, "Nenhum erro encontrado.", "red"),
    )
    c.print(table)


@shared_task
def crrection_data() -> None:
    from datetime import datetime
    from students.models import MonthlyFee, Payment, Student
    from core.settings import c

    date = datetime.now().replace(day=3).replace(month=2)

    try:
        Student.objects.all().update(created_at=date)
    except Exception as e:
        c.log(f"Erro ao atualizar Alunos {e}")

    try:
        MonthlyFee.objects.filter(paid=True).all().update(
            reference_month="02/2026", created_at=date
        )
    except Exception as e:

        c.log(f"Erro ao atualizar mensalidades {e}")

    try:
        Payment.objects.all().update(created_at=date)
    except Exception as e:
        c.log(f"Erro ao atualizar pagamentos {e}")

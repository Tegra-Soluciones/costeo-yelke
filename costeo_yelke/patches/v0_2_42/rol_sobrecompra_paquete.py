import frappe

ROL = "Comprador Yelke"


def execute():
    """Permite que la compra en PAQUETE COMPLETO pase la validación nativa.

    Un proveedor que vende la tela por rollo de 100 m obliga a comprar 100 aunque
    el lote necesite 29. ERPNext bloquea eso porque compara el renglón de la OC
    contra el renglón de la Solicitud de Material al que está ligado ("This
    document is over limit"), y su tolerancia es un PORCENTAJE -- nunca alcanza
    para un lote chico (de 29 a 100 es +245%).

    No se resolvió partiendo el renglón entre varias líneas de la solicitud porque
    entonces la orden pediría fracciones de rollo (0.29 + 0.71), que es justo lo
    que se quiere evitar. Tampoco subiendo la tolerancia del artículo, que dejaría
    pasar cualquier sobrecompra en silencio.

    Se usa el mecanismo nativo pensado para esto: quien tenga el rol de
    Stock Settings.role_allowed_to_over_deliver_receive recibe una ADVERTENCIA en
    vez de un error (ver status_updater.warn_about_bypassing_with_role). El
    candado real lo pone la app en guardar_documento_compra, y es MÁS estricto que
    el nativo: exige que el excedente esté respaldado por pendiente en TODA la
    solicitud (todos los lotes), no solo en el renglón -- así un rollo de más se
    compra cuando todavía hay prendas por hacer, y se rechaza cuando ya no.
    """
    if not frappe.db.exists("Role", ROL):
        frappe.get_doc({"doctype": "Role", "role_name": ROL}).insert(ignore_permissions=True)

    actual = frappe.db.get_single_value("Stock Settings", "role_allowed_to_over_deliver_receive")
    if not actual:
        frappe.db.set_single_value("Stock Settings", "role_allowed_to_over_deliver_receive", ROL)
        print(f"Stock Settings.role_allowed_to_over_deliver_receive = {ROL}")
    elif actual != ROL:
        # Ya había uno puesto a mano: no se pisa -- puede ser una decisión de la
        # operación, y cambiarlo en silencio alteraría quién puede sobre-recibir.
        print(f"role_allowed_to_over_deliver_receive ya estaba en {actual!r}; no se toca")

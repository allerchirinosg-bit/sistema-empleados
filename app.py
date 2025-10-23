# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 10:36:52 2025

@author: USER
"""

# app.py
import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime

DATA_FILE = "data.json"

# ---------- helpers ----------
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"employees": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_currency(x):
    return f"S/ {x:,.2f}"

def find_employee(data, emp_id):
    for e in data["employees"]:
        if e["id"] == emp_id:
            return e
    return None

def next_id(data):
    existing = [int(e["id"].split("_")[1]) for e in data["employees"] if "_" in e["id"]]
    return f"emp_{(max(existing)+1) if existing else 1}"

# ---------- data model helpers ----------
def ensure_month_record(emp, year, month):
    recs = emp.setdefault("monthly_work_records", [])
    rec = next((r for r in recs if r["year"]==year and r["month"]==month), None)
    if not rec:
        rec = {"year":year,"month":month,"days_worked":0,"advances":0.0,"loans":0.0,"payments":[]}
        recs.append(rec)
    return rec

# ---------- app ----------
st.set_page_config(page_title="Gestión Empleados", layout="wide")

st.title("Sistema de Registro y Gestión de Empleados")

data = load_data()

# --- Sidebar: Form to add employee ---
st.sidebar.header("Registrar empleado")
with st.sidebar.form("form_add"):
    name = st.text_input("Nombre completo")
    email = st.text_input("Email")
    phone = st.text_input("Teléfono")
    monthly_salary = st.number_input("Salario mensual (S/)", min_value=0.0, value=1000.0, step=50.0)
    category = st.selectbox("Categoría", ["Operario","Administrativo","Temporal","Otro"])
    submitted = st.form_submit_button("Agregar empleado")
    if submitted:
        emp = {
            "id": next_id(data),
            "name": name,
            "email": email,
            "phone": phone,
            "category": category,
            "monthly_salary": float(monthly_salary),
            "monthly_daily_wage": float(monthly_salary)/30.0,
            "monthly_work_records": []
        }
        data["employees"].append(emp)
        save_data(data)
        st.success("Empleado agregado")

# --- Main: show employees table ---
st.subheader("Lista de empleados")
employees = data.get("employees", [])
df = pd.DataFrame([{
    "id": e["id"],
    "Nombre": e["name"],
    "Email": e.get("email",""),
    "Tel": e.get("phone",""),
    "Categoría": e.get("category",""),
    "Salario mensual": e.get("monthly_salary",0.0),
    "Salario diario": round(e.get("monthly_daily_wage",0.0),2)
} for e in employees])

st.dataframe(df.drop(columns=["id"]) if not df.empty else pd.DataFrame())

# --- Actions per employee ---
st.subheader("Acciones por empleado")
col1, col2 = st.columns([2,3])

# Guardar en session_state qué empleado se está editando
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = None

with col1:
    emp_sel = st.selectbox("Seleccionar empleado", ["--"] + [f"{e['id']} - {e['name']}" for e in employees])
    if emp_sel and emp_sel != "--":
        emp_id = emp_sel.split(" - ")[0]
        emp = find_employee(data, emp_id)
        st.markdown(f"**{emp['name']}** - Salario diario: {format_currency(emp['monthly_daily_wage'])}")

        # ---- Editar info básica ----
        if st.button("Editar info básica"):
            st.session_state.edit_mode = emp_id  # activar edición

        if st.session_state.edit_mode == emp_id:
            st.markdown("### Editar información del empleado")
            with st.form("edit_basic_form"):
                new_name = st.text_input("Nombre", value=emp["name"])
                new_email = st.text_input("Email", value=emp.get("email",""))
                new_phone = st.text_input("Teléfono", value=emp.get("phone",""))
                new_salary = st.number_input("Salario mensual (S/)", value=emp.get("monthly_salary",0.0))
                save_btn = st.form_submit_button("Guardar cambios")
                if save_btn:
                    emp["name"] = new_name
                    emp["email"] = new_email
                    emp["phone"] = new_phone
                    emp["monthly_salary"] = float(new_salary)
                    emp["monthly_daily_wage"] = float(new_salary)/30.0
                    save_data(data)
                    st.success("Empleado actualizado correctamente ✅")
                    st.session_state.edit_mode = None
                    st.rerun()

        # ---- Eliminar empleado ----
        st.markdown("---")
        st.markdown("### Eliminar empleado")
        if st.button("Eliminar empleado permanentemente"):
            confirm = st.checkbox("Confirmar eliminación definitiva")
            if confirm:
                data["employees"] = [e for e in data["employees"] if e["id"] != emp_id]
                save_data(data)
                st.success("Empleado eliminado correctamente 🗑️")
                st.rerun()

with col2:
    if emp_sel and emp_sel != "--":
        emp_id = emp_sel.split(" - ")[0]
        emp = find_employee(data, emp_id)

        st.markdown("### Registrar días trabajados / adelantos / préstamos / pagos")
        c1, c2 = st.columns(2)
        with c1:
            year = st.number_input("Año", value=datetime.now().year, step=1)
            month = st.selectbox("Mes", list(range(1,13)), index=datetime.now().month-1)
            days = st.number_input("Días trabajados", value=0, step=1)  # permite negativos
        with c2:
            advances = st.number_input("Adelantos (S/)", min_value=0.0, value=0.0, step=10.0)
            loans = st.number_input("Préstamos (S/)", min_value=0.0, value=0.0, step=10.0)
            payment_amount = st.number_input("Registrar pago (S/)", min_value=0.0, value=0.0, step=10.0)

        if st.button("Guardar registro mensual"):
            rec = ensure_month_record(emp, int(year), int(month))
            rec["days_worked"] = int(days)
            rec["advances"] = float(rec.get("advances",0.0)) + float(advances)
            rec["loans"] = float(rec.get("loans",0.0)) + float(loans)
            if payment_amount and payment_amount > 0:
                rec.setdefault("payments", []).append({"date": datetime.now().isoformat(), "amount": float(payment_amount)})
            save_data(data)
            st.success("Registro mensual guardado ✅")

        # Historial mensual
        st.markdown("#### Historial (meses)")
        recs = sorted(emp.get("monthly_work_records", []), key=lambda r: (r["year"], r["month"]), reverse=True)
        for r in recs:
            daily = emp.get("monthly_daily_wage", 0.0)
            earned = r.get("days_worked",0)*daily
            payments = sum([p.get("amount",0) for p in r.get("payments",[])])
            pending = earned - r.get("advances",0.0) - r.get("loans",0.0) - payments
            st.write(f"{r['year']}-{r['month']:02d}: Días {r['days_worked']} • Ganado {format_currency(earned)} • Adelantos {format_currency(r.get('advances',0.0))} • Préstamos {format_currency(r.get('loans',0.0))} • Pagos {format_currency(payments)} • Pendiente {format_currency(pending)}")

# --- Reports & exports ---
st.subheader("Reportes mensuales y exportar")
rcol1, rcol2, rcol3 = st.columns([1,1,2])
with rcol1:
    report_year = st.number_input("Año (reporte)", value=datetime.now().year, step=1, key="r_year")
with rcol2:
    report_month = st.selectbox("Mes (reporte)", list(range(1,13)), index=datetime.now().month-1, key="r_month")
with rcol3:
    if st.button("Generar reporte"):
        # build report
        rows = []
        totals = {"employees":0,"days":0,"earned":0.0,"advances":0.0,"loans":0.0,"payments":0.0,"pending":0.0}
        for emp in data.get("employees", []):
            rec = next((r for r in emp.get("monthly_work_records",[]) if r["year"]==report_year and r["month"]==report_month), None)
            if not rec: 
                continue
            totals["employees"] += 1
            days = rec.get("days_worked",0)
            daily = emp.get("monthly_daily_wage", emp.get("monthly_salary",0.0)/30.0)
            earned = days * daily
            advances = rec.get("advances",0.0)
            loans = rec.get("loans",0.0)
            payments = sum([p.get("amount",0.0) for p in rec.get("payments",[])])
            pending = earned - advances - loans - payments
            rows.append({
                "employeeId": emp["id"],
                "name": emp["name"],
                "daysWorked": days,
                "dailyWage": round(daily,2),
                "earned": round(earned,2),
                "advances": round(advances,2),
                "loans": round(loans,2),
                "payments": round(payments,2),
                "pending": round(pending,2)
            })
            totals["days"] += days
            totals["earned"] += earned
            totals["advances"] += advances
            totals["loans"] += loans
            totals["payments"] += payments
            totals["pending"] += pending

        st.write("Resumen", totals)
        if rows:
            df_report = pd.DataFrame(rows)
            st.dataframe(df_report)

            # export CSV/JSON
            csv = df_report.to_csv(index=False).encode('utf-8')
            json_bytes = json.dumps({"monthSummary": totals, "rows": rows}, ensure_ascii=False, indent=2).encode('utf-8')
            st.download_button("Descargar CSV", csv, file_name=f"reporte_{report_year}_{report_month}.csv", mime="text/csv")
            st.download_button("Descargar JSON", json_bytes, file_name=f"reporte_{report_year}_{report_month}.json", mime="application/json")
        else:
            st.info("No hay registros para ese mes")

# --- Footer / save on changes already handled by save_data calls ---
st.markdown("---")
st.caption("Datos guardados en data.json en la carpeta del proyecto.")


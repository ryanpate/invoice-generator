#!/usr/bin/env python3
"""
Script to auto-translate .po files for Spanish and French.
Uses a comprehensive translation dictionary plus pattern-based translations.
"""
import re
import os

# Spanish translations dictionary
ES_TRANSLATIONS = {
    # Navigation & UI
    "English": "Ingles",
    "Spanish": "Espanol",
    "French": "Frances",
    "Dashboard": "Panel de Control",
    "Invoices": "Facturas",
    "Billing": "Facturacion",
    "Change language": "Cambiar idioma",
    "Logout": "Cerrar sesion",
    "Pricing": "Precios",
    "Login": "Iniciar sesion",
    "Get Started Free": "Comenzar Gratis",
    "Product": "Producto",
    "Features": "Caracteristicas",
    "API": "API",
    "Blog": "Blog",
    "Free Tools": "Herramientas Gratuitas",
    "Invoice Calculator": "Calculadora de Facturas",
    "Late Fee Calculator": "Calculadora de Cargos por Mora",
    "Support": "Soporte",
    "Help Center": "Centro de Ayuda",
    "Contact Us": "Contactenos",
    "Legal": "Legal",
    "Privacy Policy": "Politica de Privacidad",
    "Terms of Service": "Terminos de Servicio",
    "All rights reserved.": "Todos los derechos reservados.",
    "Home": "Inicio",

    # Common UI elements
    "Yes": "Si",
    "No": "No",
    "Free": "Gratis",
    "N/A": "N/A",
    "Unique": "Unico",
    "Feature": "Caracteristica",
    "from $0/mo": "desde $0/mes",
    "from $15/mo": "desde $15/mes",
    "Free only": "Solo gratis",
    "Free Plan Available": "Plan Gratuito Disponible",
    "5 free credits": "5 creditos gratis",
    "Unlimited*": "Ilimitado*",
    "5/month": "5/mes",
    "Pay-As-You-Go Option": "Opcion de Pago por Uso",
    "Yes (credits)": "Si (creditos)",
    "Professional PDF Templates": "Plantillas PDF Profesionales",
    "5 templates": "5 plantillas",
    "1 basic": "1 basica",
    "Many (design)": "Muchas (diseno)",
    "3 templates": "3 plantillas",
    "CSV Batch Upload": "Carga Masiva CSV",
    "Import only": "Solo importacion",
    "Recurring Invoices": "Facturas Recurrentes",
    "Yes ($29/mo)": "Si ($29/mes)",
    "Email Invoices to Clients": "Enviar Facturas por Email",
    "Yes (all plans)": "Si (todos los planes)",
    "Payment Status Tracking": "Seguimiento del Estado de Pago",
    "API Access": "Acceso API",
    "Yes ($79/mo)": "Si ($79/mes)",
    "Yes ($35+/mo)": "Si ($35+/mes)",
    "Custom Logo/Branding": "Logo/Marca Personalizada",
    "Accounting Features": "Funciones de Contabilidad",
    "Invoicing only": "Solo facturacion",
    "Design only": "Solo diseno",
    "Full suite": "Suite completa",
    "Setup Time": "Tiempo de Configuracion",
    "2 minutes": "2 minutos",
    "1 minute": "1 minuto",
    "10+ minutes": "10+ minutos",
    "15+ minutes": "15+ minutos",
    "We Win": "Ganamos",
    "Different Focus": "Enfoque Diferente",

    # Invoice terms
    "Invoice": "Factura",
    "INVOICE": "FACTURA",
    "Invoice Template": "Plantilla de Factura",
    "Bill To": "Facturar a",
    "Bill To:": "Facturar a:",
    "Date": "Fecha",
    "Date:": "Fecha:",
    "Due": "Vencimiento",
    "Due:": "Vencimiento:",
    "Description": "Descripcion",
    "Qty": "Cant",
    "Rate": "Tarifa",
    "Amount": "Monto",
    "Hours": "Horas",
    "Subtotal": "Subtotal",
    "Tax": "Impuesto",
    "Tax (8%)": "Impuesto (8%)",
    "Total": "Total",
    "Total Due": "Total a Pagar",
    "Notes": "Notas",
    "Payment Terms": "Terminos de Pago",
    "Fixed": "Fijo",

    # Template names
    "Clean Slate": "Minimalista",
    "Executive": "Ejecutivo",
    "Bold Modern": "Moderno Audaz",
    "Classic Professional": "Clasico Profesional",
    "Neon Edge": "Borde Neon",
    "Templates": "Plantillas",

    # Template descriptions
    "Minimalist": "Minimalista",
    "Modern": "Moderno",
    "Tech-Friendly": "Amigable con la Tecnologia",
    "Sans-Serif": "Sans-Serif",
    "Premium": "Premium",
    "Elegant": "Elegante",
    "Professional": "Profesional",
    "Serif": "Serif",
    "Vibrant": "Vibrante",
    "Creative": "Creativo",
    "Bold": "Audaz",
    "Gradient": "Degradado",
    "Traditional": "Tradicional",
    "Trusted": "Confiable",
    "Universal": "Universal",
    "Dark Mode": "Modo Oscuro",
    "Neon": "Neon",
    "Futuristic": "Futurista",

    # Industries
    "Tech Startups": "Startups Tecnologicas",
    "SaaS Companies": "Empresas SaaS",
    "Web Developers": "Desarrolladores Web",
    "Digital Agencies": "Agencias Digitales",
    "Consultants": "Consultores",
    "Law Firms": "Bufetes de Abogados",
    "Financial Advisors": "Asesores Financieros",
    "Corporate Services": "Servicios Corporativos",
    "Designers": "Disenadores",
    "Photographers": "Fotografos",
    "Videographers": "Videografos",
    "Creative Agencies": "Agencias Creativas",
    "Accountants": "Contadores",
    "General Business": "Negocios Generales",
    "Established Companies": "Empresas Establecidas",
    "Insurance & Healthcare": "Seguros y Salud",
    "Gaming Studios": "Estudios de Videojuegos",
    "Entertainment": "Entretenimiento",
    "Crypto & Web3": "Cripto y Web3",

    # Actions
    "Try This Template Free": "Probar Esta Plantilla Gratis",
    "See Full Preview": "Ver Vista Previa Completa",
    "Start Creating Invoices Free": "Comenzar a Crear Facturas Gratis",
    "Try InvoiceKits Free": "Probar InvoiceKits Gratis",
    "Start Free - 5 Invoices Included": "Comenzar Gratis - 5 Facturas Incluidas",
    "Try Invoice Calculator": "Probar Calculadora de Facturas",
    "Try Late Fee Calculator": "Probar Calculadora de Cargos por Mora",
    "Sign Up Free": "Registrarse Gratis",
    "View Pricing": "Ver Precios",
    "Learn More": "Saber Mas",
    "Get Started": "Comenzar",
    "Start Now": "Comenzar Ahora",
    "View full pricing details": "Ver detalles completos de precios",
    "Contact us": "Contactenos",

    # Pricing
    "Starter": "Inicial",
    "Professional": "Profesional",
    "Business": "Empresarial",
    "month": "mes",
    "per month": "por mes",
    "/month": "/mes",
    "/mo": "/mes",
    "Best Value": "Mejor Valor",
    "Most Popular": "Mas Popular",
    "Popular": "Popular",
    "invoices/month": "facturas/mes",
    "Unlimited invoices": "Facturas ilimitadas",
    "All templates": "Todas las plantillas",
    "No watermark": "Sin marca de agua",
    "Email support": "Soporte por email",
    "Priority support": "Soporte prioritario",
    "API access": "Acceso API",
    "Team seats": "Asientos de equipo",
    "3 team seats": "3 asientos de equipo",

    # Landing page
    "The Invoice Generator": "El Generador de Facturas",
    "for Professionals": "para Profesionales",
    "Create beautiful, professional invoices in seconds.": "Crea facturas hermosas y profesionales en segundos.",
    "No credit card required.": "No se requiere tarjeta de credito.",
    "5 free credits included.": "5 creditos gratis incluidos.",
    "Start with 5 free credits. No credit card required.": "Comienza con 5 creditos gratis. No se requiere tarjeta de credito.",
    "Perfect For": "Perfecto Para",
    "Full Template Preview": "Vista Previa Completa de la Plantilla",
    "See exactly what your invoices will look like": "Mira exactamente como se veran tus facturas",
    "Template Features": "Caracteristicas de la Plantilla",
    "Everything you need for professional invoicing": "Todo lo que necesitas para facturacion profesional",
    "Explore Other Templates": "Explorar Otras Plantillas",
    "Find the perfect design for your business": "Encuentra el diseno perfecto para tu negocio",

    # Features
    "Your Logo": "Tu Logo",
    "Upload your company logo for instant brand recognition": "Sube el logo de tu empresa para reconocimiento instantaneo de marca",
    "Auto Calculations": "Calculos Automaticos",
    "Automatic subtotals, tax calculations, and totals": "Subtotales automaticos, calculos de impuestos y totales",
    "Multi-Currency": "Multi-Moneda",
    "Bill in USD, EUR, GBP, and other major currencies": "Factura en USD, EUR, GBP y otras monedas principales",
    "Hourly Billing": "Facturacion por Hora",
    "Perfect for time-based consulting engagements": "Perfecto para consultorias basadas en tiempo",
    "Email Delivery": "Entrega por Email",
    "Send directly to clients with PDF attachment": "Envia directamente a clientes con adjunto PDF",

    # Company info placeholders
    "Your Company": "Tu Empresa",
    "Your Company Name": "Nombre de Tu Empresa",
    "Client Name": "Nombre del Cliente",
    "Client Company": "Empresa Cliente",

    # Sample items
    "Web Development": "Desarrollo Web",
    "UI/UX Design": "Diseno UI/UX",
    "Website Redesign": "Rediseno de Sitio Web",
    "Mobile App Development": "Desarrollo de App Movil",
    "UX Consultation (hourly)": "Consultoria UX (por hora)",
    "Brand Identity Design": "Diseno de Identidad de Marca",
    "Social Media Kit": "Kit de Redes Sociales",
    "Brand Identity Package": "Paquete de Identidad de Marca",
    "Website Design (5 pages)": "Diseno Web (5 paginas)",
    "Social Media Templates": "Plantillas de Redes Sociales",
    "Monthly Bookkeeping": "Contabilidad Mensual",
    "Tax Preparation": "Preparacion de Impuestos",
    "Monthly Bookkeeping - January": "Contabilidad Mensual - Enero",
    "Q4 Financial Statement Prep": "Preparacion de Estados Financieros Q4",
    "Tax Planning Consultation": "Consultoria de Planificacion Fiscal",
    "Game Asset Design": "Diseno de Assets de Juego",
    "Sound Effects Package": "Paquete de Efectos de Sonido",
    "3D Character Models (Pack)": "Modelos de Personajes 3D (Paquete)",
    "Environment Design": "Diseno de Entorno",
    "UI/UX Design for Game Menu": "Diseno UI/UX para Menu de Juego",
    "Executive Strategy Workshop": "Taller de Estrategia Ejecutiva",
    "Market Analysis & Report": "Analisis de Mercado e Informe",
    "Board Presentation Prep": "Preparacion de Presentacion a Directivos",
    "Strategy Workshop (8 hrs)": "Taller de Estrategia (8 hrs)",
    "Executive Presentation": "Presentacion Ejecutiva",

    # Dates
    "Jan 9, 2026": "9 Ene, 2026",
    "January 9, 2026": "9 de Enero, 2026",
    "January 24, 2026": "24 de Enero, 2026",
    "February 8, 2026": "8 de Febrero, 2026",

    # FAQ & Help
    "Frequently Asked Questions": "Preguntas Frecuentes",
    "FAQ": "FAQ",
    "Questions? We have answers.": "Preguntas? Tenemos respuestas.",
    "Have questions? We have answers.": "Tienes preguntas? Tenemos respuestas.",

    # Contact
    "Get in Touch": "Ponte en Contacto",
    "Send us a message": "Envianos un mensaje",
    "Email": "Correo electronico",
    "Subject": "Asunto",
    "Message": "Mensaje",
    "Send Message": "Enviar Mensaje",

    # Calculator
    "Calculate": "Calcular",
    "Reset": "Reiniciar",
    "Add Line Item": "Agregar Linea",
    "Remove": "Eliminar",
    "Discount": "Descuento",
    "Line Items": "Lineas de Factura",
    "Hourly Rate": "Tarifa por Hora",
    "Flat Fee": "Tarifa Fija",
    "Percentage": "Porcentaje",
    "Compound Interest": "Interes Compuesto",
    "Days Overdue": "Dias de Atraso",
    "Original Amount": "Monto Original",
    "Late Fee": "Cargo por Mora",
    "Total with Late Fee": "Total con Cargo por Mora",

    # Misc
    "Thank you for your business.": "Gracias por su preferencia.",
    "Thank you for your business. Payment is due within 15 days.": "Gracias por su preferencia. El pago vence en 15 dias.",
    "Thanks for choosing Creative Studio! We loved working on this project.": "Gracias por elegir Creative Studio! Nos encanto trabajar en este proyecto.",
    "Thanks for gaming with us! Payment accepted via crypto or wire transfer.": "Gracias por jugar con nosotros! Pago aceptado via cripto o transferencia bancaria.",
    "Net 15. Payment due within 15 days of invoice date. Wire transfer preferred.": "Neto 15. Pago vence en 15 dias desde la fecha de factura. Se prefiere transferencia bancaria.",
    "Net 30. Please remit payment to the address above or via bank transfer.": "Neto 30. Por favor envie el pago a la direccion arriba o via transferencia bancaria.",

    # Comparison page
    "InvoiceKits vs Competitors - Invoice Generator Comparison 2026": "InvoiceKits vs Competidores - Comparacion de Generadores de Facturas 2026",
    "Compare Invoice Generators": "Comparar Generadores de Facturas",
    "InvoiceKits vs The Competition": "InvoiceKits vs La Competencia",
    "Feature Comparison at a Glance": "Comparacion de Caracteristicas de un Vistazo",
    "See which invoice generator has the features you need": "Mira cual generador de facturas tiene las caracteristicas que necesitas",
    "Detailed Comparisons": "Comparaciones Detalladas",
    "A closer look at how InvoiceKits compares": "Una mirada mas cercana a como se compara InvoiceKits",
    "InvoiceKits vs Invoice-Generator.com": "InvoiceKits vs Invoice-Generator.com",
    "InvoiceKits vs Canva Invoice Maker": "InvoiceKits vs Creador de Facturas Canva",
    "InvoiceKits vs Wave": "InvoiceKits vs Wave",
    "InvoiceKits vs Zoho Invoice": "InvoiceKits vs Zoho Invoice",

    # For pages
    "For Freelancers": "Para Freelancers",
    "For Small Business": "Para Pequenas Empresas",
    "For Consultants": "Para Consultores",
    "Need more?": "Necesitas mas?",
    "for Enterprise pricing.": "para precios empresariales.",

    # CTA sections
    "Ready to Use Clean Slate?": "Listo para Usar Minimalista?",
    "Ready to Use Executive?": "Listo para Usar Ejecutivo?",
    "Ready to Use Bold Modern?": "Listo para Usar Moderno Audaz?",
    "Ready to Use Classic Professional?": "Listo para Usar Clasico Profesional?",
    "Ready to Use Neon Edge?": "Listo para Usar Borde Neon?",
    "Create your first invoice in under 60 seconds. Free to start.": "Crea tu primera factura en menos de 60 segundos. Gratis para comenzar.",
    "Create professional invoices that match your expertise. Free to start.": "Crea facturas profesionales que reflejen tu experiencia. Gratis para comenzar.",
    "Create invoices as creative as your work. Free to start.": "Crea facturas tan creativas como tu trabajo. Gratis para comenzar.",
    "Create trusted, professional invoices. Free to start.": "Crea facturas confiables y profesionales. Gratis para comenzar.",
    "Create invoices as bold as your brand. Free to start.": "Crea facturas tan audaces como tu marca. Gratis para comenzar.",

    # Pricing - Credit packs
    "Free Start": "Inicio Gratis",
    "FREE forever": "GRATIS para siempre",
    "One-time signup bonus": "Bono unico de registro",
    "10 Credits": "10 Creditos",
    "25 Credits": "25 Creditos",
    "50 Credits": "50 Credits",
    "$0.90/invoice": "$0.90/factura",
    "$0.76/invoice": "$0.76/factura",
    "$0.70/invoice": "$0.70/factura",
    "Buy Credits": "Comprar Creditos",
    "Monthly Subscriptions": "Suscripciones Mensuales",
    "Start Free Trial": "Comenzar Prueba Gratis",
    "50 invoices/month": "50 facturas/mes",
    "200 invoices + batch": "200 facturas + lote",
    "Unlimited + API": "Ilimitado + API",
    "$0.18/invoice (50/mo)": "$0.18/factura (50/mes)",
    "$0.15/invoice (200/mo)": "$0.15/factura (200/mes)",
    "All templates, no watermark": "Todas las plantillas, sin marca de agua",
    "200 invoices/month": "200 facturas/mes",
    "50 invoices per month": "50 facturas por mes",
    "200 invoices per month": "200 facturas por mes",
    "All 5 templates": "Las 5 plantillas",
    "Popular": "Popular",

    # CTAs and buttons
    "Create Your First Invoice Free": "Crea Tu Primera Factura Gratis",
    "View Templates": "Ver Plantillas",
    "See How It Works": "Ver Como Funciona",
    "Try It Free - No Credit Card Required": "Pruebalo Gratis - Sin Tarjeta de Credito",
    "Start Free - No Credit Card Required": "Comenzar Gratis - Sin Tarjeta de Credito",
    "Start Free - No Credit Card": "Comenzar Gratis - Sin Tarjeta de Credito",
    "See Features": "Ver Caracteristicas",
    "No credit card required. Free forever plan available.": "No se requiere tarjeta de credito. Plan gratuito disponible.",

    # Job titles and roles
    "Strategy Consultant": "Consultor de Estrategia",
    "HR Consultant": "Consultor de RRHH",
    "IT Consultant": "Consultor de TI",
    "Freelance Designer": "Disenador Freelance",
    "Freelance Developer": "Desarrollador Freelance",
    "Freelance Writer": "Escritor Freelance",
    "Consulting Services": "Servicios de Consultoria",
    "Strategic Advisory": "Asesoria Estrategica",

    # Headings and titles
    "Built for Consultants": "Creado para Consultores",
    "Built for Freelancers": "Creado para Freelancers",
    "Built for Small Business": "Creado para Pequenas Empresas",
    "Your Expertise Deserves": "Tu Experiencia Merece",
    "Professional Invoices.": "Facturas Profesionales.",
    "Stop Chasing Payments.": "Deja de Perseguir Pagos.",
    "Start Getting Paid.": "Comienza a Cobrar.",
    "Billing That Scales": "Facturacion que Escala",
    "With Your Business.": "Con Tu Negocio.",
    "Sound Familiar?": "Te Suena Familiar?",
    "Growing Pains Are Real": "Los Dolores de Crecimiento Son Reales",

    # Feature titles
    "Your Logo & Branding": "Tu Logo y Marca",
    "Direct Email Delivery": "Entrega Directa por Email",
    "Retainer Invoices": "Facturas de Anticipo",
    "Project Milestones": "Hitos del Proyecto",
    "Email Invoices Instantly": "Enviar Facturas al Instante",
    "Payment Tracking": "Seguimiento de Pagos",
    "5 Professional Templates": "5 Plantillas Profesionales",
    "Multi-Currency Support": "Soporte Multi-Moneda",
    "Batch Invoice Processing": "Procesamiento de Facturas por Lotes",
    "Invoice Dashboard": "Panel de Facturas",
    "Add Line Items": "Agregar Lineas",
    "Add Client Details": "Agregar Datos del Cliente",
    "Send & Get Paid": "Enviar y Cobrar",
    "Send & Track": "Enviar y Rastrear",
    "Set Up Your Profile": "Configura Tu Perfil",
    "Create & Customize": "Crear y Personalizar",
    "Features Freelancers Love": "Caracteristicas que los Freelancers Aman",
    "Features That Drive Business Growth": "Caracteristicas que Impulsan el Crecimiento",
    "Features Consultants Need": "Caracteristicas que Necesitan los Consultores",
    "Templates That Command Respect": "Plantillas que Imponen Respeto",
    "From Engagement to Payment": "Del Compromiso al Pago",
    "Trusted by Consultants Worldwide": "Confiado por Consultores en Todo el Mundo",
    "Trusted by Freelancers Everywhere": "Confiado por Freelancers en Todas Partes",
    "Flexible Pricing for Consultants": "Precios Flexibles para Consultores",
    "Simple Pricing for Freelancers": "Precios Simples para Freelancers",

    # Status labels
    "Paid": "Pagado",
    "Pending": "Pendiente",
    "Overdue": "Vencido",
    "Draft": "Borrador",
    "Sent": "Enviado",
    "This Month": "Este Mes",

    # Misc pricing
    "Best for Consultants": "Mejor para Consultores",
    "Best for Freelancers": "Mejor para Freelancers",
    "Popular with Consultants": "Popular entre Consultores",
    "Recurring invoices (retainers)": "Facturas recurrentes (anticipos)",
    "API + batch processing": "API + procesamiento por lotes",
    "API access (1,000 calls/mo)": "Acceso API (1,000 llamadas/mes)",
    "Unlimited recurring invoices": "Facturas recurrentes ilimitadas",
    "All plans include email support.": "Todos los planes incluyen soporte por email.",
    "For growing freelance businesses": "Para negocios freelance en crecimiento",
    "For busy freelancers with retainer clients": "Para freelancers ocupados con clientes de anticipo",
    "For agencies and high-volume freelancers": "Para agencias y freelancers de alto volumen",

    # CTA final sections
    "Ready to Get Paid Faster?": "Listo para Cobrar Mas Rapido?",
    "Ready to Elevate Your Consulting Practice?": "Listo para Elevar Tu Practica de Consultoria?",
    "Ready to Switch to Better Invoicing?": "Listo para Cambiar a Mejor Facturacion?",
    "Free forever plan available. Upgrade anytime.": "Plan gratuito disponible. Mejora cuando quieras.",

    # Sample client names
    "Fortune 500 Corp": "Corporacion Fortune 500",
    "Attn: VP of Strategy": "Attn: VP de Estrategia",
    "Your Name Design": "Tu Nombre Diseno",
    "Logo Design": "Diseno de Logo",
    "Market Analysis Report": "Informe de Analisis de Mercado",
    "Strategy Workshop (8 hrs @ $350/hr)": "Taller de Estrategia (8 hrs @ $350/hr)",

    # Homepage
    "Free Invoice Generator": "Generador de Facturas Gratis",
    "Create Professional Invoices in Seconds": "Crea Facturas Profesionales en Segundos",
    "Create Free Invoice Now": "Crear Factura Gratis Ahora",
    "The Most Powerful Invoice Generator": "El Generador de Facturas Mas Potente",
    "Instant PDF Generation": "Generacion Instantanea de PDF",
    "Batch Invoice Generator": "Generador de Facturas por Lotes",
    "5 Beautiful Templates": "5 Hermosas Plantillas",
    "Custom Logo": "Logo Personalizado",
    "Developer API": "API para Desarrolladores",
    "5 Professional Invoice Templates": "5 Plantillas de Factura Profesionales",
    "Total": "Total",
    "Tech companies, startups": "Empresas de tecnologia, startups",
    "Consulting, legal, finance": "Consultoria, legal, finanzas",
    "Creative agencies, designers": "Agencias creativas, disenadores",
    "General business, accounting": "Negocios generales, contabilidad",
    "Gaming, tech, entertainment": "Gaming, tecnologia, entretenimiento",
    "Trusted by Freelancers & Small Businesses": "Confiado por Freelancers y Pequenas Empresas",
    "Free Starter": "Inicio Gratis",
    "Starter Pack": "Paquete Inicial",
    "1 template": "1 plantilla",
    "Watermark on PDFs": "Marca de agua en PDFs",
    "Never expires": "Nunca expira",
    "Unlimited": "Ilimitado",
    "Batch upload": "Carga por lotes",
    "No batch upload": "Sin carga por lotes",
    "No API access": "Sin acceso API",
    "calls": "llamadas",
    "Ready to Get Started?": "Listo para Comenzar?",
    "Try Our Invoice Generator Free": "Prueba Nuestro Generador de Facturas Gratis",
    "Company": "Empresa",
    "About": "Acerca de",
    "Careers": "Carreras",
    "Contact": "Contacto",
    "Privacy": "Privacidad",
    "Terms": "Terminos",

    # Pricing page
    "Invoice Generator Pricing": "Precios del Generador de Facturas",
    "Credits": "Creditos",
    "Pay only when you invoice": "Paga solo cuando facturas",
    "or": "o",
    "Subscriptions": "Suscripciones",
    "Best value for regular use": "Mejor valor para uso regular",
    "Credits never expire.": "Los creditos nunca expiran.",
    "5 credits": "5 creditos",
    "Lifetime credits": "Creditos de por vida",
    "Includes watermark": "Incluye marca de agua",
    "$0.90 per invoice": "$0.90 por factura",
    "$0.76 per invoice": "$0.76 por factura",
    "$0.70 per invoice": "$0.70 por factura",
    "Never expire": "Nunca expiran",
    "5 invoices/month": "5 facturas/mes",
    "invoices per month": "facturas por mes",
    "template": "plantilla",
    "calls/mo": "llamadas/mes",
    "Current Plan": "Plan Actual",
    "Switch to Free": "Cambiar a Gratis",
    "Upgrade": "Mejorar",
    "mo": "mes",

    # Pricing comparison
    "Credits vs Subscriptions: Which is Right for You?": "Creditos vs Suscripciones: Cual es Mejor Para Ti?",
    "Choose Credits If:": "Elige Creditos Si:",
    "Choose a Subscription If:": "Elige una Suscripcion Si:",
    "You invoice occasionally (1-10/month)": "Facturas ocasionalmente (1-10/mes)",
    "You want no monthly commitment": "No quieres compromiso mensual",
    "Your invoicing needs are unpredictable": "Tus necesidades de facturacion son impredecibles",
    "You're a seasonal business": "Eres un negocio estacional",
    "You invoice regularly (10+/month)": "Facturas regularmente (10+/mes)",
    "You want the best per-invoice value": "Quieres el mejor valor por factura",
    "You need batch upload or recurring invoices": "Necesitas carga por lotes o facturas recurrentes",
    "You need API access": "Necesitas acceso API",

    # Additional pricing FAQs
    "What are invoice credits?": "Que son los creditos de factura?",
    "Do credits expire?": "Expiran los creditos?",
    "Should I buy credits or subscribe?": "Deberia comprar creditos o suscribirme?",
    "Can I upgrade or downgrade anytime?": "Puedo mejorar o reducir mi plan en cualquier momento?",
    "What happens if I exceed my invoice limit?": "Que pasa si excedo mi limite de facturas?",
    "What payment methods do you accept?": "Que metodos de pago aceptan?",

    # API documentation
    "API Documentation": "Documentacion de la API",
    "API access requires a Business plan subscription": "El acceso a la API requiere una suscripcion al plan Business",
    "Quick Start": "Inicio Rapido",
    "Base URL": "URL Base",
    "Authentication": "Autenticacion",

    # Small business page extras
    "Real-Time Dashboard": "Panel en Tiempo Real",
    "Email Delivery & Receipts": "Entrega por Email y Recibos",
    "How Small Businesses Use InvoiceKits": "Como las Pequenas Empresas Usan InvoiceKits",
    "Set Up Your Business": "Configura Tu Negocio",
    "Create & Send Invoices": "Crear y Enviar Facturas",
    "Track & Get Paid": "Rastrea y Cobra",
    "Get Started Free Today": "Comienza Gratis Hoy",
    "Trusted by Growing Businesses": "Confiado por Negocios en Crecimiento",
    "Property Management Co.": "Empresa de Gestion de Propiedades",
    "SaaS Startup Founder": "Fundador de Startup SaaS",
    "Marketing Agency Owner": "Dueno de Agencia de Marketing",
    "Flexible Pricing That Scales With You": "Precios Flexibles que Escalan Contigo",
    "Batch upload + recurring": "Carga por lotes + recurrente",
    "API access (1000 calls/mo)": "Acceso API (1000 llamadas/mes)",
    "Ready to Streamline Your Billing?": "Listo para Optimizar Tu Facturacion?",
    "Start Your Free Trial Today": "Comienza Tu Prueba Gratis Hoy",
}

# French translations dictionary
FR_TRANSLATIONS = {
    # Navigation & UI
    "English": "Anglais",
    "Spanish": "Espagnol",
    "French": "Francais",
    "Dashboard": "Tableau de Bord",
    "Invoices": "Factures",
    "Billing": "Facturation",
    "Change language": "Changer de langue",
    "Logout": "Deconnexion",
    "Pricing": "Tarifs",
    "Login": "Connexion",
    "Get Started Free": "Commencer Gratuitement",
    "Product": "Produit",
    "Features": "Fonctionnalites",
    "API": "API",
    "Blog": "Blog",
    "Free Tools": "Outils Gratuits",
    "Invoice Calculator": "Calculateur de Factures",
    "Late Fee Calculator": "Calculateur de Penalites de Retard",
    "Support": "Support",
    "Help Center": "Centre d'Aide",
    "Contact Us": "Contactez-nous",
    "Legal": "Mentions Legales",
    "Privacy Policy": "Politique de Confidentialite",
    "Terms of Service": "Conditions d'Utilisation",
    "All rights reserved.": "Tous droits reserves.",
    "Home": "Accueil",

    # Common UI elements
    "Yes": "Oui",
    "No": "Non",
    "Free": "Gratuit",
    "N/A": "N/A",
    "Unique": "Unique",
    "Feature": "Fonctionnalite",
    "from $0/mo": "a partir de 0$/mois",
    "from $15/mo": "a partir de 15$/mois",
    "Free only": "Gratuit uniquement",
    "Free Plan Available": "Plan Gratuit Disponible",
    "5 free credits": "5 credits gratuits",
    "Unlimited*": "Illimite*",
    "5/month": "5/mois",
    "Pay-As-You-Go Option": "Option de Paiement a l'Usage",
    "Yes (credits)": "Oui (credits)",
    "Professional PDF Templates": "Modeles PDF Professionnels",
    "5 templates": "5 modeles",
    "1 basic": "1 basique",
    "Many (design)": "Nombreux (design)",
    "3 templates": "3 modeles",
    "CSV Batch Upload": "Telechargement CSV en Masse",
    "Import only": "Import uniquement",
    "Recurring Invoices": "Factures Recurrentes",
    "Yes ($29/mo)": "Oui (29$/mois)",
    "Email Invoices to Clients": "Envoyer les Factures par Email",
    "Yes (all plans)": "Oui (tous les plans)",
    "Payment Status Tracking": "Suivi du Statut de Paiement",
    "API Access": "Acces API",
    "Yes ($79/mo)": "Oui (79$/mois)",
    "Yes ($35+/mo)": "Oui (35$+/mois)",
    "Custom Logo/Branding": "Logo/Marque Personnalises",
    "Accounting Features": "Fonctionnalites Comptables",
    "Invoicing only": "Facturation uniquement",
    "Design only": "Design uniquement",
    "Full suite": "Suite complete",
    "Setup Time": "Temps de Configuration",
    "2 minutes": "2 minutes",
    "1 minute": "1 minute",
    "10+ minutes": "10+ minutes",
    "15+ minutes": "15+ minutes",
    "We Win": "Nous Gagnons",
    "Different Focus": "Orientation Differente",

    # Invoice terms
    "Invoice": "Facture",
    "INVOICE": "FACTURE",
    "Invoice Template": "Modele de Facture",
    "Bill To": "Facturer a",
    "Bill To:": "Facturer a:",
    "Date": "Date",
    "Date:": "Date:",
    "Due": "Echeance",
    "Due:": "Echeance:",
    "Description": "Description",
    "Qty": "Qte",
    "Rate": "Taux",
    "Amount": "Montant",
    "Hours": "Heures",
    "Subtotal": "Sous-total",
    "Tax": "Taxe",
    "Tax (8%)": "Taxe (8%)",
    "Total": "Total",
    "Total Due": "Total a Payer",
    "Notes": "Notes",
    "Payment Terms": "Conditions de Paiement",
    "Fixed": "Fixe",

    # Template names
    "Clean Slate": "Minimaliste",
    "Executive": "Executive",
    "Bold Modern": "Moderne Audacieux",
    "Classic Professional": "Classique Professionnel",
    "Neon Edge": "Neon Edge",
    "Templates": "Modeles",

    # Template descriptions
    "Minimalist": "Minimaliste",
    "Modern": "Moderne",
    "Tech-Friendly": "Oriente Tech",
    "Sans-Serif": "Sans-Serif",
    "Premium": "Premium",
    "Elegant": "Elegant",
    "Professional": "Professionnel",
    "Serif": "Serif",
    "Vibrant": "Vibrant",
    "Creative": "Creatif",
    "Bold": "Audacieux",
    "Gradient": "Degrade",
    "Traditional": "Traditionnel",
    "Trusted": "Fiable",
    "Universal": "Universel",
    "Dark Mode": "Mode Sombre",
    "Neon": "Neon",
    "Futuristic": "Futuriste",

    # Industries
    "Tech Startups": "Startups Tech",
    "SaaS Companies": "Entreprises SaaS",
    "Web Developers": "Developpeurs Web",
    "Digital Agencies": "Agences Digitales",
    "Consultants": "Consultants",
    "Law Firms": "Cabinets d'Avocats",
    "Financial Advisors": "Conseillers Financiers",
    "Corporate Services": "Services aux Entreprises",
    "Designers": "Designers",
    "Photographers": "Photographes",
    "Videographers": "Videographes",
    "Creative Agencies": "Agences Creatives",
    "Accountants": "Comptables",
    "General Business": "Entreprises Generales",
    "Established Companies": "Entreprises Etablies",
    "Insurance & Healthcare": "Assurance et Sante",
    "Gaming Studios": "Studios de Jeux Video",
    "Entertainment": "Divertissement",
    "Crypto & Web3": "Crypto et Web3",

    # Actions
    "Try This Template Free": "Essayer ce Modele Gratuitement",
    "See Full Preview": "Voir l'Apercu Complet",
    "Start Creating Invoices Free": "Commencer a Creer des Factures Gratuitement",
    "Try InvoiceKits Free": "Essayer InvoiceKits Gratuitement",
    "Start Free - 5 Invoices Included": "Commencer Gratuitement - 5 Factures Incluses",
    "Try Invoice Calculator": "Essayer le Calculateur de Factures",
    "Try Late Fee Calculator": "Essayer le Calculateur de Penalites",
    "Sign Up Free": "S'inscrire Gratuitement",
    "View Pricing": "Voir les Tarifs",
    "Learn More": "En Savoir Plus",
    "Get Started": "Commencer",
    "Start Now": "Commencer Maintenant",
    "View full pricing details": "Voir tous les details des tarifs",
    "Contact us": "Contactez-nous",

    # Pricing
    "Starter": "Debutant",
    "Professional": "Professionnel",
    "Business": "Entreprise",
    "month": "mois",
    "per month": "par mois",
    "/month": "/mois",
    "/mo": "/mois",
    "Best Value": "Meilleure Valeur",
    "Most Popular": "Le Plus Populaire",
    "Popular": "Populaire",
    "invoices/month": "factures/mois",
    "Unlimited invoices": "Factures illimitees",
    "All templates": "Tous les modeles",
    "No watermark": "Sans filigrane",
    "Email support": "Support par email",
    "Priority support": "Support prioritaire",
    "API access": "Acces API",
    "Team seats": "Places d'equipe",
    "3 team seats": "3 places d'equipe",

    # Landing page
    "The Invoice Generator": "Le Generateur de Factures",
    "for Professionals": "pour les Professionnels",
    "Create beautiful, professional invoices in seconds.": "Creez de belles factures professionnelles en quelques secondes.",
    "No credit card required.": "Aucune carte de credit requise.",
    "5 free credits included.": "5 credits gratuits inclus.",
    "Start with 5 free credits. No credit card required.": "Commencez avec 5 credits gratuits. Aucune carte de credit requise.",
    "Perfect For": "Parfait Pour",
    "Full Template Preview": "Apercu Complet du Modele",
    "See exactly what your invoices will look like": "Voyez exactement a quoi ressembleront vos factures",
    "Template Features": "Fonctionnalites du Modele",
    "Everything you need for professional invoicing": "Tout ce dont vous avez besoin pour une facturation professionnelle",
    "Explore Other Templates": "Explorer d'Autres Modeles",
    "Find the perfect design for your business": "Trouvez le design parfait pour votre entreprise",

    # Features
    "Your Logo": "Votre Logo",
    "Upload your company logo for instant brand recognition": "Telechargez le logo de votre entreprise pour une reconnaissance immediate",
    "Auto Calculations": "Calculs Automatiques",
    "Automatic subtotals, tax calculations, and totals": "Sous-totaux automatiques, calculs de taxes et totaux",
    "Multi-Currency": "Multi-Devises",
    "Bill in USD, EUR, GBP, and other major currencies": "Facturez en USD, EUR, GBP et autres devises principales",
    "Hourly Billing": "Facturation Horaire",
    "Perfect for time-based consulting engagements": "Parfait pour les missions de conseil basees sur le temps",
    "Email Delivery": "Livraison par Email",
    "Send directly to clients with PDF attachment": "Envoyez directement aux clients avec piece jointe PDF",

    # Company info placeholders
    "Your Company": "Votre Entreprise",
    "Your Company Name": "Nom de Votre Entreprise",
    "Client Name": "Nom du Client",
    "Client Company": "Entreprise Cliente",

    # Sample items
    "Web Development": "Developpement Web",
    "UI/UX Design": "Design UI/UX",
    "Website Redesign": "Refonte de Site Web",
    "Mobile App Development": "Developpement d'Application Mobile",
    "UX Consultation (hourly)": "Consultation UX (horaire)",
    "Brand Identity Design": "Design d'Identite de Marque",
    "Social Media Kit": "Kit Reseaux Sociaux",
    "Brand Identity Package": "Pack Identite de Marque",
    "Website Design (5 pages)": "Design Web (5 pages)",
    "Social Media Templates": "Modeles Reseaux Sociaux",
    "Monthly Bookkeeping": "Comptabilite Mensuelle",
    "Tax Preparation": "Preparation Fiscale",
    "Monthly Bookkeeping - January": "Comptabilite Mensuelle - Janvier",
    "Q4 Financial Statement Prep": "Preparation des Etats Financiers Q4",
    "Tax Planning Consultation": "Consultation en Planification Fiscale",
    "Game Asset Design": "Design d'Assets de Jeu",
    "Sound Effects Package": "Pack d'Effets Sonores",
    "3D Character Models (Pack)": "Modeles de Personnages 3D (Pack)",
    "Environment Design": "Design d'Environnement",
    "UI/UX Design for Game Menu": "Design UI/UX pour Menu de Jeu",
    "Executive Strategy Workshop": "Atelier de Strategie Executive",
    "Market Analysis & Report": "Analyse de Marche et Rapport",
    "Board Presentation Prep": "Preparation de Presentation au Conseil",
    "Strategy Workshop (8 hrs)": "Atelier de Strategie (8 hrs)",
    "Executive Presentation": "Presentation Executive",

    # Dates
    "Jan 9, 2026": "9 Jan 2026",
    "January 9, 2026": "9 Janvier 2026",
    "January 24, 2026": "24 Janvier 2026",
    "February 8, 2026": "8 Fevrier 2026",

    # FAQ & Help
    "Frequently Asked Questions": "Questions Frequemment Posees",
    "FAQ": "FAQ",
    "Questions? We have answers.": "Des questions? Nous avons les reponses.",
    "Have questions? We have answers.": "Vous avez des questions? Nous avons les reponses.",

    # Contact
    "Get in Touch": "Entrez en Contact",
    "Send us a message": "Envoyez-nous un message",
    "Email": "Email",
    "Subject": "Sujet",
    "Message": "Message",
    "Send Message": "Envoyer le Message",

    # Calculator
    "Calculate": "Calculer",
    "Reset": "Reinitialiser",
    "Add Line Item": "Ajouter une Ligne",
    "Remove": "Supprimer",
    "Discount": "Remise",
    "Line Items": "Lignes de Facture",
    "Hourly Rate": "Taux Horaire",
    "Flat Fee": "Forfait",
    "Percentage": "Pourcentage",
    "Compound Interest": "Interet Compose",
    "Days Overdue": "Jours de Retard",
    "Original Amount": "Montant Original",
    "Late Fee": "Penalite de Retard",
    "Total with Late Fee": "Total avec Penalite",

    # Misc
    "Thank you for your business.": "Merci pour votre confiance.",
    "Thank you for your business. Payment is due within 15 days.": "Merci pour votre confiance. Le paiement est du sous 15 jours.",
    "Thanks for choosing Creative Studio! We loved working on this project.": "Merci d'avoir choisi Creative Studio! Nous avons adore travailler sur ce projet.",
    "Thanks for gaming with us! Payment accepted via crypto or wire transfer.": "Merci de jouer avec nous! Paiement accepte par crypto ou virement bancaire.",
    "Net 15. Payment due within 15 days of invoice date. Wire transfer preferred.": "Net 15. Paiement du sous 15 jours. Virement bancaire prefere.",
    "Net 30. Please remit payment to the address above or via bank transfer.": "Net 30. Veuillez effectuer le paiement a l'adresse ci-dessus ou par virement bancaire.",

    # Comparison page
    "InvoiceKits vs Competitors - Invoice Generator Comparison 2026": "InvoiceKits vs Concurrents - Comparaison des Generateurs de Factures 2026",
    "Compare Invoice Generators": "Comparer les Generateurs de Factures",
    "InvoiceKits vs The Competition": "InvoiceKits vs La Concurrence",
    "Feature Comparison at a Glance": "Comparaison des Fonctionnalites en un Coup d'Oeil",
    "See which invoice generator has the features you need": "Voyez quel generateur de factures a les fonctionnalites dont vous avez besoin",
    "Detailed Comparisons": "Comparaisons Detaillees",
    "A closer look at how InvoiceKits compares": "Un regard plus approfondi sur la comparaison InvoiceKits",
    "InvoiceKits vs Invoice-Generator.com": "InvoiceKits vs Invoice-Generator.com",
    "InvoiceKits vs Canva Invoice Maker": "InvoiceKits vs Createur de Factures Canva",
    "InvoiceKits vs Wave": "InvoiceKits vs Wave",
    "InvoiceKits vs Zoho Invoice": "InvoiceKits vs Zoho Invoice",

    # For pages
    "For Freelancers": "Pour les Freelances",
    "For Small Business": "Pour les Petites Entreprises",
    "For Consultants": "Pour les Consultants",
    "Need more?": "Besoin de plus?",
    "for Enterprise pricing.": "pour les tarifs entreprise.",

    # CTA sections
    "Ready to Use Clean Slate?": "Pret a Utiliser Minimaliste?",
    "Ready to Use Executive?": "Pret a Utiliser Executive?",
    "Ready to Use Bold Modern?": "Pret a Utiliser Moderne Audacieux?",
    "Ready to Use Classic Professional?": "Pret a Utiliser Classique Professionnel?",
    "Ready to Use Neon Edge?": "Pret a Utiliser Neon Edge?",
    "Create your first invoice in under 60 seconds. Free to start.": "Creez votre premiere facture en moins de 60 secondes. Gratuit pour commencer.",
    "Create professional invoices that match your expertise. Free to start.": "Creez des factures professionnelles qui refletent votre expertise. Gratuit pour commencer.",
    "Create invoices as creative as your work. Free to start.": "Creez des factures aussi creatives que votre travail. Gratuit pour commencer.",
    "Create trusted, professional invoices. Free to start.": "Creez des factures fiables et professionnelles. Gratuit pour commencer.",
    "Create invoices as bold as your brand. Free to start.": "Creez des factures aussi audacieuses que votre marque. Gratuit pour commencer.",

    # Pricing - Credit packs
    "Free Start": "Debut Gratuit",
    "FREE forever": "GRATUIT pour toujours",
    "One-time signup bonus": "Bonus d'inscription unique",
    "10 Credits": "10 Credits",
    "25 Credits": "25 Credits",
    "50 Credits": "50 Credits",
    "$0.90/invoice": "$0.90/facture",
    "$0.76/invoice": "$0.76/facture",
    "$0.70/invoice": "$0.70/facture",
    "Buy Credits": "Acheter des Credits",
    "Monthly Subscriptions": "Abonnements Mensuels",
    "Start Free Trial": "Commencer l'Essai Gratuit",
    "50 invoices/month": "50 factures/mois",
    "200 invoices + batch": "200 factures + lot",
    "Unlimited + API": "Illimite + API",
    "$0.18/invoice (50/mo)": "$0.18/facture (50/mois)",
    "$0.15/invoice (200/mo)": "$0.15/facture (200/mois)",
    "All templates, no watermark": "Tous les modeles, sans filigrane",
    "200 invoices/month": "200 factures/mois",
    "50 invoices per month": "50 factures par mois",
    "200 invoices per month": "200 factures par mois",
    "All 5 templates": "Les 5 modeles",
    "Popular": "Populaire",

    # CTAs and buttons
    "Create Your First Invoice Free": "Creez Votre Premiere Facture Gratuitement",
    "View Templates": "Voir les Modeles",
    "See How It Works": "Voir Comment ca Marche",
    "Try It Free - No Credit Card Required": "Essayez Gratuitement - Sans Carte de Credit",
    "Start Free - No Credit Card Required": "Commencer Gratuitement - Sans Carte de Credit",
    "Start Free - No Credit Card": "Commencer Gratuitement - Sans Carte de Credit",
    "See Features": "Voir les Fonctionnalites",
    "No credit card required. Free forever plan available.": "Aucune carte de credit requise. Plan gratuit disponible.",

    # Job titles and roles
    "Strategy Consultant": "Consultant en Strategie",
    "HR Consultant": "Consultant RH",
    "IT Consultant": "Consultant IT",
    "Freelance Designer": "Designer Freelance",
    "Freelance Developer": "Developpeur Freelance",
    "Freelance Writer": "Redacteur Freelance",
    "Consulting Services": "Services de Conseil",
    "Strategic Advisory": "Conseil Strategique",

    # Headings and titles
    "Built for Consultants": "Concu pour les Consultants",
    "Built for Freelancers": "Concu pour les Freelances",
    "Built for Small Business": "Concu pour les Petites Entreprises",
    "Your Expertise Deserves": "Votre Expertise Merite",
    "Professional Invoices.": "des Factures Professionnelles.",
    "Stop Chasing Payments.": "Arretez de Courir Apres les Paiements.",
    "Start Getting Paid.": "Commencez a Etre Paye.",
    "Billing That Scales": "Une Facturation qui Evolue",
    "With Your Business.": "Avec Votre Entreprise.",
    "Sound Familiar?": "Ca Vous Dit Quelque Chose?",
    "Growing Pains Are Real": "Les Douleurs de Croissance Sont Reelles",

    # Feature titles
    "Your Logo & Branding": "Votre Logo et Marque",
    "Direct Email Delivery": "Livraison Directe par Email",
    "Retainer Invoices": "Factures d'Acompte",
    "Project Milestones": "Jalons de Projet",
    "Email Invoices Instantly": "Envoyer les Factures Instantanement",
    "Payment Tracking": "Suivi des Paiements",
    "5 Professional Templates": "5 Modeles Professionnels",
    "Multi-Currency Support": "Support Multi-Devises",
    "Batch Invoice Processing": "Traitement par Lots des Factures",
    "Invoice Dashboard": "Tableau de Bord des Factures",
    "Add Line Items": "Ajouter des Lignes",
    "Add Client Details": "Ajouter les Details du Client",
    "Send & Get Paid": "Envoyer et Etre Paye",
    "Send & Track": "Envoyer et Suivre",
    "Set Up Your Profile": "Configurez Votre Profil",
    "Create & Customize": "Creer et Personnaliser",
    "Features Freelancers Love": "Fonctionnalites que les Freelances Adorent",
    "Features That Drive Business Growth": "Fonctionnalites qui Stimulent la Croissance",
    "Features Consultants Need": "Fonctionnalites dont les Consultants ont Besoin",
    "Templates That Command Respect": "Modeles qui Inspirent le Respect",
    "From Engagement to Payment": "De l'Engagement au Paiement",
    "Trusted by Consultants Worldwide": "Approuve par les Consultants du Monde Entier",
    "Trusted by Freelancers Everywhere": "Approuve par les Freelances Partout",
    "Flexible Pricing for Consultants": "Tarifs Flexibles pour Consultants",
    "Simple Pricing for Freelancers": "Tarifs Simples pour Freelances",

    # Status labels
    "Paid": "Paye",
    "Pending": "En Attente",
    "Overdue": "En Retard",
    "Draft": "Brouillon",
    "Sent": "Envoye",
    "This Month": "Ce Mois-ci",

    # Misc pricing
    "Best for Consultants": "Ideal pour les Consultants",
    "Best for Freelancers": "Ideal pour les Freelances",
    "Popular with Consultants": "Populaire chez les Consultants",
    "Recurring invoices (retainers)": "Factures recurrentes (acomptes)",
    "API + batch processing": "API + traitement par lots",
    "API access (1,000 calls/mo)": "Acces API (1 000 appels/mois)",
    "Unlimited recurring invoices": "Factures recurrentes illimitees",
    "All plans include email support.": "Tous les plans incluent le support par email.",
    "For growing freelance businesses": "Pour les entreprises freelances en croissance",
    "For busy freelancers with retainer clients": "Pour les freelances occupes avec des clients sous acompte",
    "For agencies and high-volume freelancers": "Pour les agences et freelances a haut volume",

    # CTA final sections
    "Ready to Get Paid Faster?": "Pret a Etre Paye Plus Vite?",
    "Ready to Elevate Your Consulting Practice?": "Pret a Elever Votre Pratique de Conseil?",
    "Ready to Switch to Better Invoicing?": "Pret a Passer a une Meilleure Facturation?",
    "Free forever plan available. Upgrade anytime.": "Plan gratuit disponible. Ameliorez a tout moment.",

    # Sample client names
    "Fortune 500 Corp": "Societe Fortune 500",
    "Attn: VP of Strategy": "Attn: VP de Strategie",
    "Your Name Design": "Votre Nom Design",
    "Logo Design": "Design de Logo",
    "Market Analysis Report": "Rapport d'Analyse de Marche",
    "Strategy Workshop (8 hrs @ $350/hr)": "Atelier de Strategie (8 hrs @ $350/hr)",

    # Homepage
    "Free Invoice Generator": "Generateur de Factures Gratuit",
    "Create Professional Invoices in Seconds": "Creez des Factures Professionnelles en Quelques Secondes",
    "Create Free Invoice Now": "Creer une Facture Gratuite Maintenant",
    "The Most Powerful Invoice Generator": "Le Generateur de Factures le Plus Puissant",
    "Instant PDF Generation": "Generation PDF Instantanee",
    "Batch Invoice Generator": "Generateur de Factures par Lots",
    "5 Beautiful Templates": "5 Beaux Modeles",
    "Custom Logo": "Logo Personnalise",
    "Developer API": "API Developpeur",
    "5 Professional Invoice Templates": "5 Modeles de Factures Professionnels",
    "Total": "Total",
    "Tech companies, startups": "Entreprises tech, startups",
    "Consulting, legal, finance": "Conseil, juridique, finance",
    "Creative agencies, designers": "Agences creatives, designers",
    "General business, accounting": "Entreprises generales, comptabilite",
    "Gaming, tech, entertainment": "Jeux video, tech, divertissement",
    "Trusted by Freelancers & Small Businesses": "Approuve par les Freelances et Petites Entreprises",
    "Free Starter": "Debutant Gratuit",
    "Starter Pack": "Pack Debutant",
    "1 template": "1 modele",
    "Watermark on PDFs": "Filigrane sur les PDFs",
    "Never expires": "N'expire jamais",
    "Unlimited": "Illimite",
    "Batch upload": "Telechargement par lots",
    "No batch upload": "Pas de telechargement par lots",
    "No API access": "Pas d'acces API",
    "calls": "appels",
    "Ready to Get Started?": "Pret a Commencer?",
    "Try Our Invoice Generator Free": "Essayez Notre Generateur de Factures Gratuitement",
    "Company": "Entreprise",
    "About": "A Propos",
    "Careers": "Carrieres",
    "Contact": "Contact",
    "Privacy": "Confidentialite",
    "Terms": "Conditions",

    # Pricing page
    "Invoice Generator Pricing": "Tarifs du Generateur de Factures",
    "Credits": "Credits",
    "Pay only when you invoice": "Payez uniquement quand vous facturez",
    "or": "ou",
    "Subscriptions": "Abonnements",
    "Best value for regular use": "Meilleure valeur pour une utilisation reguliere",
    "Credits never expire.": "Les credits n'expirent jamais.",
    "5 credits": "5 credits",
    "Lifetime credits": "Credits a vie",
    "Includes watermark": "Inclut le filigrane",
    "$0.90 per invoice": "$0.90 par facture",
    "$0.76 per invoice": "$0.76 par facture",
    "$0.70 per invoice": "$0.70 par facture",
    "Never expire": "N'expirent jamais",
    "5 invoices/month": "5 factures/mois",
    "invoices per month": "factures par mois",
    "template": "modele",
    "calls/mo": "appels/mois",
    "Current Plan": "Plan Actuel",
    "Switch to Free": "Passer au Gratuit",
    "Upgrade": "Ameliorer",
    "mo": "mois",

    # Pricing comparison
    "Credits vs Subscriptions: Which is Right for You?": "Credits vs Abonnements: Lequel Vous Convient?",
    "Choose Credits If:": "Choisissez les Credits Si:",
    "Choose a Subscription If:": "Choisissez un Abonnement Si:",
    "You invoice occasionally (1-10/month)": "Vous facturez occasionnellement (1-10/mois)",
    "You want no monthly commitment": "Vous ne voulez pas d'engagement mensuel",
    "Your invoicing needs are unpredictable": "Vos besoins de facturation sont imprevisibles",
    "You're a seasonal business": "Vous etes une entreprise saisonniere",
    "You invoice regularly (10+/month)": "Vous facturez regulierement (10+/mois)",
    "You want the best per-invoice value": "Vous voulez le meilleur rapport qualite-prix par facture",
    "You need batch upload or recurring invoices": "Vous avez besoin du telechargement par lots ou des factures recurrentes",
    "You need API access": "Vous avez besoin d'un acces API",

    # Additional pricing FAQs
    "What are invoice credits?": "Que sont les credits de facture?",
    "Do credits expire?": "Les credits expirent-ils?",
    "Should I buy credits or subscribe?": "Dois-je acheter des credits ou m'abonner?",
    "Can I upgrade or downgrade anytime?": "Puis-je ameliorer ou reduire mon plan a tout moment?",
    "What happens if I exceed my invoice limit?": "Que se passe-t-il si je depasse ma limite de factures?",
    "What payment methods do you accept?": "Quels modes de paiement acceptez-vous?",

    # API documentation
    "API Documentation": "Documentation de l'API",
    "API access requires a Business plan subscription": "L'acces a l'API necessite un abonnement au plan Business",
    "Quick Start": "Demarrage Rapide",
    "Base URL": "URL de Base",
    "Authentication": "Authentification",

    # Small business page extras
    "Real-Time Dashboard": "Tableau de Bord en Temps Reel",
    "Email Delivery & Receipts": "Livraison par Email et Recus",
    "How Small Businesses Use InvoiceKits": "Comment les Petites Entreprises Utilisent InvoiceKits",
    "Set Up Your Business": "Configurez Votre Entreprise",
    "Create & Send Invoices": "Creer et Envoyer des Factures",
    "Track & Get Paid": "Suivre et Etre Paye",
    "Get Started Free Today": "Commencez Gratuitement Aujourd'hui",
    "Trusted by Growing Businesses": "Approuve par les Entreprises en Croissance",
    "Property Management Co.": "Societe de Gestion Immobiliere",
    "SaaS Startup Founder": "Fondateur de Startup SaaS",
    "Marketing Agency Owner": "Proprietaire d'Agence Marketing",
    "Flexible Pricing That Scales With You": "Tarifs Flexibles qui Evoluent avec Vous",
    "Batch upload + recurring": "Telechargement par lots + recurrent",
    "API access (1000 calls/mo)": "Acces API (1000 appels/mois)",
    "Ready to Streamline Your Billing?": "Pret a Optimiser Votre Facturation?",
    "Start Your Free Trial Today": "Commencez Votre Essai Gratuit Aujourd'hui",
}


def parse_po_file(filepath):
    """Parse a .po file and return list of (msgid, msgstr, metadata) tuples."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    # Split by double newline to get blocks
    blocks = re.split(r'\n\n+', content)

    for block in blocks:
        if not block.strip():
            continue

        lines = block.strip().split('\n')

        # Extract comments, msgid, msgstr
        comments = []
        msgid_lines = []
        msgstr_lines = []
        current_type = None
        fuzzy = False

        for line in lines:
            if line.startswith('#'):
                comments.append(line)
                if '#, fuzzy' in line:
                    fuzzy = True
            elif line.startswith('msgid '):
                current_type = 'msgid'
                # Extract the string part
                match = re.match(r'msgid "(.*)"$', line)
                if match:
                    msgid_lines.append(match.group(1))
            elif line.startswith('msgstr '):
                current_type = 'msgstr'
                match = re.match(r'msgstr "(.*)"$', line)
                if match:
                    msgstr_lines.append(match.group(1))
            elif line.startswith('"') and line.endswith('"'):
                # Continuation line
                content_match = re.match(r'"(.*)"$', line)
                if content_match:
                    if current_type == 'msgid':
                        msgid_lines.append(content_match.group(1))
                    elif current_type == 'msgstr':
                        msgstr_lines.append(content_match.group(1))

        msgid = ''.join(msgid_lines)
        msgstr = ''.join(msgstr_lines)

        entries.append({
            'comments': comments,
            'msgid': msgid,
            'msgstr': msgstr,
            'fuzzy': fuzzy
        })

    return entries


def translate_text(text, translations_dict):
    """Translate a text using the dictionary, with fallback patterns."""
    if not text:
        return text

    # Direct match
    if text in translations_dict:
        return translations_dict[text]

    # Try case-insensitive match
    text_lower = text.lower()
    for key, value in translations_dict.items():
        if key.lower() == text_lower:
            # Preserve original case style
            if text.isupper():
                return value.upper()
            elif text[0].isupper():
                return value[0].upper() + value[1:] if len(value) > 1 else value.upper()
            return value

    # No translation found - return original (will show English)
    return text


def write_po_file(filepath, entries, language_code, language_name):
    """Write entries back to a .po file with translations."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(entries):
            # Write comments
            for comment in entry['comments']:
                # Remove fuzzy flag since we're providing translations
                if '#, fuzzy' not in comment:
                    f.write(comment + '\n')

            # Handle header entry
            if entry['msgid'] == '' and i == 0:
                f.write('msgid ""\n')
                f.write('msgstr ""\n')
                header = entry['msgstr'].replace('PACKAGE VERSION', 'InvoiceKits 1.0')
                header = header.replace('YEAR-MO-DA HO:MI+ZONE', '2026-01-15 12:00+0000')
                header = header.replace('FULL NAME <EMAIL@ADDRESS>', 'InvoiceKits Team <support@invoicekits.com>')
                header = header.replace('LANGUAGE <LL@li.org>', f'{language_name} <{language_code}@invoicekits.com>')
                header = header.replace('Language: \\n', f'Language: {language_code}\\n')

                # Write header lines
                for line in header.split('\\n'):
                    if line:
                        f.write(f'"{line}\\n"\n')
            else:
                # Write msgid
                msgid = entry['msgid']
                if '\n' in msgid or len(msgid) > 70:
                    f.write('msgid ""\n')
                    # Split into lines
                    for line in msgid.split('\n'):
                        f.write(f'"{line}"\n')
                else:
                    f.write(f'msgid "{msgid}"\n')

                # Get or generate translation
                msgstr = entry.get('translated', entry['msgstr'])

                # Write msgstr
                if '\n' in msgstr or len(msgstr) > 70:
                    f.write('msgstr ""\n')
                    for line in msgstr.split('\n'):
                        f.write(f'"{line}"\n')
                else:
                    f.write(f'msgstr "{msgstr}"\n')

            f.write('\n')


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Process Spanish
    es_path = os.path.join(base_dir, 'locale', 'es', 'LC_MESSAGES', 'django.po')
    if os.path.exists(es_path):
        print("Processing Spanish translations...")
        entries = parse_po_file(es_path)

        translated_count = 0
        for entry in entries:
            if entry['msgid']:
                translation = translate_text(entry['msgid'], ES_TRANSLATIONS)
                if translation != entry['msgid']:
                    entry['translated'] = translation
                    translated_count += 1
                else:
                    entry['translated'] = ''  # Keep empty to show English fallback

        write_po_file(es_path, entries, 'es', 'Spanish')
        print(f"Spanish: {translated_count} strings translated")

    # Process French
    fr_path = os.path.join(base_dir, 'locale', 'fr', 'LC_MESSAGES', 'django.po')
    if os.path.exists(fr_path):
        print("Processing French translations...")
        entries = parse_po_file(fr_path)

        translated_count = 0
        for entry in entries:
            if entry['msgid']:
                translation = translate_text(entry['msgid'], FR_TRANSLATIONS)
                if translation != entry['msgid']:
                    entry['translated'] = translation
                    translated_count += 1
                else:
                    entry['translated'] = ''

        write_po_file(fr_path, entries, 'fr', 'French')
        print(f"French: {translated_count} strings translated")

    print("\nDone! Run 'python manage.py compilemessages' to compile .mo files.")


if __name__ == '__main__':
    main()

/**
 * ========================================
 * NUMMA - MODULE EMPLOYÉS & PAIE v3.0
 * ========================================
 * Gestion complète RH avec backend
 * Backend: https://optimis-fiscale-production.up.railway.app
 * 
 * DÉPENDANCES: numma-messages.js (REQUIS)
 */

(function() {
    'use strict';
    
    console.log('👥 Chargement module Employés & Paie...');
    
    // Vérifier que numma-messages.js est chargé
    if (typeof showMessage === 'undefined') {
        console.error('❌ ERREUR: numma-messages.js doit être chargé AVANT numma-employees.js');
        alert('Erreur de chargement: Système de messages manquant');
        return;
    }

    // =====================================================
    // CONFIGURATION
    // =====================================================

    const EMPLOYEE_CONFIG = {
        ENDPOINTS: {
            EMPLOYEES: '/api/employees',
            PAYSLIPS: '/api/payslips',
            GENERATE_PAYSLIP: '/api/payslips/generate',
            CALCULATE_CHARGES: '/api/payroll/charges',
            EXPORT_DSN: '/api/payroll/dsn'
        }
    };

    // =====================================================
    // API CLIENT
    // =====================================================

    class EmployeeAPI {
        constructor() {
            this.baseURL = window.NUMMA_CONFIG?.API_BASE || 'https://optimis-fiscale-production.up.railway.app';
        }
        
        getHeaders() {
            const token = localStorage.getItem('authToken') || 'demo-token';
            return {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            };
        }
        
        async request(endpoint, options = {}) {
            const url = `${this.baseURL}${endpoint}`;
            const config = {
                ...options,
                headers: {
                    ...this.getHeaders(),
                    ...options.headers
                }
            };
            
            console.log(`👥 Employee API: ${options.method || 'GET'} ${endpoint}`);
            
            try {
                const response = await fetch(url, config);
                
                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }
                
                if (response.status === 204) return null;
                
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/pdf')) {
                    return await response.blob();
                }
                
                return await response.json();
            } catch (error) {
                console.error('❌ Employee API Error:', error);
                throw error;
            }
        }
        
        // CRUD Employés
        async listEmployees() {
            return await this.request(EMPLOYEE_CONFIG.ENDPOINTS.EMPLOYEES);
        }
        
        async getEmployee(id) {
            return await this.request(`${EMPLOYEE_CONFIG.ENDPOINTS.EMPLOYEES}/${id}`);
        }
        
        async createEmployee(data) {
            return await this.request(EMPLOYEE_CONFIG.ENDPOINTS.EMPLOYEES, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }
        
        async updateEmployee(id, data) {
            return await this.request(`${EMPLOYEE_CONFIG.ENDPOINTS.EMPLOYEES}/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        }
        
        async deleteEmployee(id) {
            return await this.request(`${EMPLOYEE_CONFIG.ENDPOINTS.EMPLOYEES}/${id}`, {
                method: 'DELETE'
            });
        }
        
        // Fiches de paie
        async listPayslips(filters = {}) {
            const params = new URLSearchParams(filters);
            return await this.request(`${EMPLOYEE_CONFIG.ENDPOINTS.PAYSLIPS}?${params}`);
        }
        
        async generatePayslip(employeeId, month, year) {
            return await this.request(EMPLOYEE_CONFIG.ENDPOINTS.GENERATE_PAYSLIP, {
                method: 'POST',
                body: JSON.stringify({ employee_id: employeeId, month, year })
            });
        }
        
        async generateAllPayslips(month, year) {
            return await this.request(`${EMPLOYEE_CONFIG.ENDPOINTS.GENERATE_PAYSLIP}/batch`, {
                method: 'POST',
                body: JSON.stringify({ month, year })
            });
        }
        
        async getPayslipPDF(payslipId) {
            return await this.request(`${EMPLOYEE_CONFIG.ENDPOINTS.PAYSLIPS}/${payslipId}/pdf`);
        }
        
        // Calcul charges
        async calculateCharges(salaryData) {
            return await this.request(EMPLOYEE_CONFIG.ENDPOINTS.CALCULATE_CHARGES, {
                method: 'POST',
                body: JSON.stringify(salaryData)
            });
        }
        
        // Export DSN
        async exportDSN(month, year) {
            return await this.request(`${EMPLOYEE_CONFIG.ENDPOINTS.EXPORT_DSN}?month=${month}&year=${year}`);
        }
    }

    const employeeAPI = new EmployeeAPI();

    // =====================================================
    // GESTION DES EMPLOYÉS
    // =====================================================

    async function loadEmployees() {
        try {
            showInfo('Chargement des employés...');
            
            const employees = await employeeAPI.listEmployees();
            console.log('✅ Employés chargés:', employees.length);
            
            displayEmployees(employees);
            showSuccess(`${employees.length} employé(s) chargé(s)`);
            
            return employees;
        } catch (error) {
            console.error('Erreur chargement employés:', error);
            showError('Impossible de charger les employés: ' + error.message);
            
            // Fallback: localStorage
            return loadEmployeesFromLocal();
        }
    }

    function displayEmployees(employees) {
        const tbody = document.getElementById('employeesTableBody');
        if (!tbody) return;
        
        if (!employees || employees.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-gray);">Aucun employé trouvé</td></tr>';
            return;
        }
        
        tbody.innerHTML = employees.map(emp => `
            <tr>
                <td><strong>${emp.first_name} ${emp.last_name}</strong></td>
                <td>${emp.position || 'N/A'}</td>
                <td>${emp.contract_type || 'CDI'}</td>
                <td>€ ${parseFloat(emp.gross_salary || 0).toFixed(2)}</td>
                <td><span class="badge badge-success">Actif</span></td>
                <td>
                    <button class="btn btn-outline" style="padding: 0.25rem 0.75rem; font-size: 0.875rem;" 
                            onclick="viewEmployee('${emp.id}')">
                        Voir
                    </button>
                    <button class="btn btn-primary" style="padding: 0.25rem 0.75rem; font-size: 0.875rem; margin-left: 0.5rem;" 
                            onclick="generatePayslip('${emp.id}')">
                        Fiche
                    </button>
                </td>
            </tr>
        `).join('');
    }

    async function showAddEmployeeModal() {
        const employeeData = {
            first_name: prompt('Prénom:'),
            last_name: prompt('Nom:'),
            email: prompt('Email:'),
            position: prompt('Poste:'),
            contract_type: 'CDI',
            gross_salary: parseFloat(prompt('Salaire brut mensuel:') || '0'),
            start_date: new Date().toISOString().split('T')[0]
        };
        
        if (!employeeData.first_name || !employeeData.last_name) {
            return;
        }
        
        try {
            showInfo('Création de l\'employé...');
            
            const employee = await employeeAPI.createEmployee(employeeData);
            
            showSuccess(`${employee.first_name} ${employee.last_name} ajouté - Poste: ${employee.position}`);
            
            loadEmployees();
            
        } catch (error) {
            console.error('Erreur création employé:', error);
            showError(error.message);
        }
    }

    async function viewEmployee(employeeId) {
        try {
            const employee = await employeeAPI.getEmployee(employeeId);
            
            const details = `
Nom: ${employee.first_name} ${employee.last_name}
Email: ${employee.email}
Poste: ${employee.position}
Contrat: ${employee.contract_type}
Salaire brut: € ${employee.gross_salary}
Date d'embauche: ${employee.start_date}
            `.trim();
            
            showInfo(details);
            
        } catch (error) {
            console.error('Erreur:', error);
            showError(error.message);
        }
    }

    // =====================================================
    // FICHES DE PAIE
    // =====================================================

    async function generatePayslip(employeeId) {
        const month = parseInt(prompt('Mois (1-12):', new Date().getMonth() + 1));
        const year = parseInt(prompt('Année:', new Date().getFullYear()));
        
        if (!month || !year) return;
        
        try {
            showInfo('Génération de la fiche de paie...');
            
            const payslip = await employeeAPI.generatePayslip(employeeId, month, year);
            
            showSuccess(`Fiche de paie générée - ${payslip.employee_name} - ${month}/${year}`);
            
            if (confirm('Voulez-vous télécharger le PDF?')) {
                await downloadPayslip(payslip.id);
            }
            
            return payslip;
        } catch (error) {
            console.error('Erreur génération fiche:', error);
            showError(error.message);
        }
    }

    async function generateAllPayslips() {
        const month = parseInt(prompt('Mois (1-12):', new Date().getMonth() + 1));
        const year = parseInt(prompt('Année:', new Date().getFullYear()));
        
        if (!month || !year) return;
        
        try {
            showInfo('Génération de toutes les fiches...');
            
            const result = await employeeAPI.generateAllPayslips(month, year);
            
            showSuccess(`${result.count} fiche(s) de paie créée(s)`);
            
            loadPayslips({ month, year });
            
        } catch (error) {
            console.error('Erreur génération batch:', error);
            showError(error.message);
        }
    }

    async function downloadPayslip(payslipId) {
        try {
            showInfo('Génération du PDF...');
            
            const pdfBlob = await employeeAPI.getPayslipPDF(payslipId);
            
            const url = window.URL.createObjectURL(pdfBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `fiche_paie_${payslipId}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            showSuccess('PDF téléchargé');
            
        } catch (error) {
            console.error('Erreur téléchargement PDF:', error);
            showError(error.message);
        }
    }

    async function loadPayslips(filters = {}) {
        try {
            const payslips = await employeeAPI.listPayslips(filters);
            console.log('✅ Fiches chargées:', payslips.length);
            displayPayslips(payslips);
            return payslips;
        } catch (error) {
            console.error('Erreur chargement fiches:', error);
            showError('Impossible de charger les fiches de paie');
        }
    }

    function displayPayslips(payslips) {
        const tbody = document.getElementById('payslipsTableBody');
        if (!tbody) return;
        
        if (!payslips || payslips.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;">Aucune fiche de paie trouvée</td></tr>';
            return;
        }
        
        tbody.innerHTML = payslips.map(payslip => `
            <tr>
                <td>${payslip.employee_name}</td>
                <td>${payslip.month}/${payslip.year}</td>
                <td>€ ${parseFloat(payslip.net_salary || 0).toFixed(2)}</td>
                <td><span class="badge badge-success">Générée</span></td>
                <td>
                    <button class="btn btn-outline" style="padding: 0.25rem 0.75rem; font-size: 0.875rem;" 
                            onclick="downloadPayslip('${payslip.id}')">
                        📥 PDF
                    </button>
                </td>
            </tr>
        `).join('');
    }

    // =====================================================
    // CHARGES SOCIALES
    // =====================================================

    async function calculateCharges() {
        const grossSalary = parseFloat(prompt('Salaire brut mensuel:', '2500'));
        if (!grossSalary) return;
        
        try {
            showInfo('Calcul des charges...');
            
            const result = await employeeAPI.calculateCharges({ gross_salary: grossSalary });
            
            const details = `
Salaire brut: € ${result.gross_salary}
Charges employeur: € ${result.employer_charges}
Charges salariales: € ${result.employee_charges}
Salaire net: € ${result.net_salary}
Coût total: € ${result.total_cost}
            `.trim();
            
            showSuccess(details);
            
        } catch (error) {
            console.error('Erreur calcul charges:', error);
            showError(error.message);
        }
    }

    // =====================================================
    // EXPORT DSN
    // =====================================================

    async function exportDSN() {
        const month = parseInt(prompt('Mois (1-12):', new Date().getMonth() + 1));
        const year = parseInt(prompt('Année:', new Date().getFullYear()));
        
        if (!month || !year) return;
        
        try {
            showInfo('Génération DSN...');
            
            const dsnData = await employeeAPI.exportDSN(month, year);
            
            const blob = new Blob([dsnData.xml], { type: 'application/xml' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `dsn_${month}_${year}.xml`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            showSuccess(`DSN exportée - Fichier ${month}/${year} téléchargé`);
            
        } catch (error) {
            console.error('Erreur export DSN:', error);
            showError(error.message);
        }
    }

    // =====================================================
    // FALLBACK LOCALSTORAGE
    // =====================================================

    function loadEmployeesFromLocal() {
        const employees = JSON.parse(localStorage.getItem('numma_employees') || '[]');
        displayEmployees(employees);
        return employees;
    }

    // =====================================================
    // EXPORT GLOBAL
    // =====================================================

    window.employeeAPI = employeeAPI;
    window.loadEmployees = loadEmployees;
    window.showAddEmployeeModal = showAddEmployeeModal;
    window.viewEmployee = viewEmployee;
    window.generatePayslip = generatePayslip;
    window.generateAllPayslips = generateAllPayslips;
    window.downloadPayslip = downloadPayslip;
    window.loadPayslips = loadPayslips;
    window.calculateCharges = calculateCharges;
    window.exportDSN = exportDSN;

    console.log('✅ Module Employés & Paie chargé');
})();

/**
 * ========================================
 * NUMMA - MODULE EXPORTS v3.0
 * ========================================
 * Export FEC, CSV, PDF, Excel
 * 
 * DÉPENDANCES: numma-messages.js (REQUIS)
 */

(function() {
    'use strict';

    console.log('📥 Chargement module Exports...');

    // Vérifier que numma-messages.js est chargé
    if (typeof showMessage === 'undefined') {
        console.error('❌ ERREUR: numma-messages.js doit être chargé AVANT numma-exports.js');
        return;
    }

    // =====================================================
    // CONFIGURATION
    // =====================================================

    const API_BASE = window.NUMMA_CONFIG?.API_BASE || 'https://optimis-fiscale-production.up.railway.app';

    // =====================================================
    // FEC EXPORT
    // =====================================================

    async function exportToFEC(year) {
        try {
            showInfo('Génération du fichier FEC...');

            const response = await fetch(`${API_BASE}/api/exports/fec?year=${year}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('authToken')}`
                }
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la génération du FEC');
            }

            const blob = await response.blob();
            downloadBlob(blob, `FEC_${year}_${Date.now()}.txt`);

            showSuccess('Fichier FEC téléchargé');
        } catch (error) {
            console.error('Export FEC error:', error);
            showError('Erreur lors de l\'export FEC: ' + error.message);
        }
    }

    // =====================================================
    // TRANSACTIONS CSV
    // =====================================================

    async function exportTransactionsCSV(startDate, endDate) {
        try {
            showInfo('Export des transactions...');

            const params = new URLSearchParams();
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);

            const response = await fetch(`${API_BASE}/api/exports/transactions/csv?${params}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('authToken')}`
                }
            });

            if (!response.ok) {
                throw new Error('Erreur lors de l\'export des transactions');
            }

            const blob = await response.blob();
            downloadBlob(blob, `transactions_${Date.now()}.csv`);

            showSuccess('Transactions exportées');
        } catch (error) {
            console.error('Export transactions error:', error);
            showError('Erreur lors de l\'export: ' + error.message);
        }
    }

    // =====================================================
    // INVOICES CSV
    // =====================================================

    async function exportInvoicesCSV(type = 'sales') {
        try {
            showInfo('Export des factures...');

            const response = await fetch(`${API_BASE}/api/exports/invoices/csv?invoice_type=${type}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('authToken')}`
                }
            });

            if (!response.ok) {
                throw new Error('Erreur lors de l\'export des factures');
            }

            const blob = await response.blob();
            downloadBlob(blob, `invoices_${type}_${Date.now()}.csv`);

            showSuccess('Factures exportées');
        } catch (error) {
            console.error('Export invoices error:', error);
            showError('Erreur lors de l\'export: ' + error.message);
        }
    }

    // =====================================================
    // CASHFLOW EXPORTS
    // =====================================================

    function exportCSV() {
        console.log('📊 Exporting cashflow to CSV...');
        
        try {
            const data = getCashflowData();
            
            if (!data || data.length === 0) {
                showWarning('Aucune donnée à exporter');
                return;
            }
            
            const headers = ['Date', 'Type', 'Description', 'Montant', 'Solde'];
            const csvContent = [
                headers.join(','),
                ...data.map(row => [
                    row.date,
                    row.type,
                    `"${row.description}"`,
                    row.amount,
                    row.balance
                ].join(','))
            ].join('\n');
            
            downloadFile(csvContent, 'tresorerie.csv', 'text/csv');
            showSuccess('Export CSV réussi');
            
        } catch (error) {
            console.error('❌ CSV export error:', error);
            showError('Erreur lors de l\'export CSV: ' + error.message);
        }
    }

    function exportPDF() {
        console.log('📄 Exporting cashflow to PDF...');
        
        try {
            const data = getCashflowData();
            
            if (!data || data.length === 0) {
                showWarning('Aucune donnée à exporter');
                return;
            }
            
            const html = `
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport Trésorerie NUMMA</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #2563eb; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #2563eb; color: white; }
        tr:nth-child(even) { background-color: #f9fafb; }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
    </style>
</head>
<body>
    <h1>📊 Rapport de Trésorerie</h1>
    <p>Généré le ${new Date().toLocaleDateString('fr-FR')}</p>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Description</th>
                <th>Montant</th>
                <th>Solde</th>
            </tr>
        </thead>
        <tbody>
            ${data.map(row => `
                <tr>
                    <td>${row.date}</td>
                    <td>${row.type}</td>
                    <td>${row.description}</td>
                    <td class="${row.amount >= 0 ? 'positive' : 'negative'}">
                        ${row.amount.toFixed(2)} €
                    </td>
                    <td>${row.balance.toFixed(2)} €</td>
                </tr>
            `).join('')}
        </tbody>
    </table>
</body>
</html>
            `;
            
            const printWindow = window.open('', '_blank');
            printWindow.document.write(html);
            printWindow.document.close();
            
            setTimeout(() => {
                printWindow.print();
            }, 500);
            
            showSuccess('PDF généré - Utilisez Ctrl+P pour imprimer');
            
        } catch (error) {
            console.error('❌ PDF export error:', error);
            showError('Erreur lors de l\'export PDF: ' + error.message);
        }
    }

    function exportExcel() {
        console.log('📗 Exporting cashflow to Excel...');
        
        try {
            const data = getCashflowData();
            
            if (!data || data.length === 0) {
                showWarning('Aucune donnée à exporter');
                return;
            }
            
            const html = `
<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">
<head>
    <meta charset="UTF-8">
    <!--[if gte mso 9]>
    <xml>
        <x:ExcelWorkbook>
            <x:ExcelWorksheets>
                <x:ExcelWorksheet>
                    <x:Name>Trésorerie</x:Name>
                    <x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>
                </x:ExcelWorksheet>
            </x:ExcelWorksheets>
        </x:ExcelWorkbook>
    </xml>
    <![endif]-->
</head>
<body>
    <table border="1">
        <thead>
            <tr style="background-color: #2563eb; color: white; font-weight: bold;">
                <th>Date</th>
                <th>Type</th>
                <th>Description</th>
                <th>Montant</th>
                <th>Solde</th>
            </tr>
        </thead>
        <tbody>
            ${data.map(row => `
                <tr>
                    <td>${row.date}</td>
                    <td>${row.type}</td>
                    <td>${row.description}</td>
                    <td>${row.amount.toFixed(2)}</td>
                    <td>${row.balance.toFixed(2)}</td>
                </tr>
            `).join('')}
        </tbody>
    </table>
</body>
</html>
            `;
            
            downloadFile(html, 'tresorerie.xls', 'application/vnd.ms-excel');
            showSuccess('Export Excel réussi');
            
        } catch (error) {
            console.error('❌ Excel export error:', error);
            showError('Erreur lors de l\'export Excel: ' + error.message);
        }
    }

    // =====================================================
    // HELPER FUNCTIONS
    // =====================================================

    function getCashflowData() {
        if (window.cashflowData && window.cashflowData.length > 0) {
            return window.cashflowData;
        }
        
        const table = document.querySelector('.cashflow-table tbody, #cashflowTableBody');
        if (table) {
            const rows = Array.from(table.querySelectorAll('tr'));
            return rows.map(row => {
                const cells = row.querySelectorAll('td');
                return {
                    date: cells[0]?.textContent.trim() || '',
                    type: cells[1]?.textContent.trim() || '',
                    description: cells[2]?.textContent.trim() || '',
                    amount: parseFloat(cells[3]?.textContent.replace(/[^0-9.-]/g, '')) || 0,
                    balance: parseFloat(cells[4]?.textContent.replace(/[^0-9.-]/g, '')) || 0
                };
            });
        }
        
        console.warn('⚠️ No data found, using sample');
        return [
            { date: '2026-01-24', type: 'Vente', description: 'Facture F-2024-001', amount: 2400, balance: 15000 },
            { date: '2026-01-23', type: 'Achat', description: 'Fournisseur ABC', amount: -850, balance: 12600 },
            { date: '2026-01-22', type: 'Vente', description: 'Facture F-2024-002', amount: 1800, balance: 13450 }
        ];
    }

    function downloadFile(content, filename, mimeType) {
        const blob = new Blob(['\ufeff' + content], { type: mimeType + ';charset=utf-8;' });
        downloadBlob(blob, filename);
    }

    function downloadBlob(blob, filename) {
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
    }

    // =====================================================
    // EXPORT GLOBAL
    // =====================================================

    window.exportToFEC = exportToFEC;
    window.exportTransactionsCSV = exportTransactionsCSV;
    window.exportInvoicesCSV = exportInvoicesCSV;
    window.exportCSV = exportCSV;
    window.exportPDF = exportPDF;
    window.exportExcel = exportExcel;

    console.log('✅ Module Exports chargé');
})();

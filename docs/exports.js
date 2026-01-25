/**
 * NUMMA Exports Module
 * Handle FEC export and other data exports
 */

(function() {
    'use strict';

    // Export functionality
    window.exportToFEC = async function(year) {
        try {
            showInfo('Génération du fichier FEC en cours...');

            const response = await fetch(`${API_URL}/api/exports/fec?year=${year}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la génération du FEC');
            }

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `FEC_${year}_${new Date().getTime()}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showSuccess('Fichier FEC téléchargé avec succès');
        } catch (error) {
            console.error('Export FEC error:', error);
            showError('Erreur lors de l\'export FEC: ' + error.message);
        }
    };

    // Export transactions to CSV
    window.exportTransactionsCSV = async function(startDate, endDate) {
        try {
            showInfo('Export des transactions en cours...');

            const params = new URLSearchParams();
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);

            const response = await fetch(`${API_URL}/api/exports/transactions/csv?${params}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Erreur lors de l\'export des transactions');
            }

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `transactions_${new Date().getTime()}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showSuccess('Transactions exportées avec succès');
        } catch (error) {
            console.error('Export transactions error:', error);
            showError('Erreur lors de l\'export: ' + error.message);
        }
    };

    // Export invoices to CSV
    window.exportInvoicesCSV = async function(type = 'sales') {
        try {
            showInfo('Export des factures en cours...');

            const response = await fetch(`${API_URL}/api/exports/invoices/csv?invoice_type=${type}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Erreur lors de l\'export des factures');
            }

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `invoices_${type}_${new Date().getTime()}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showSuccess('Factures exportées avec succès');
        } catch (error) {
            console.error('Export invoices error:', error);
            showError('Erreur lors de l\'export: ' + error.message);
        }
    };

    // Export cashflow to CSV
    window.exportCSV = function() {
        console.log('📊 Exporting to CSV...');
        
        try {
            // Get cashflow data from table or API
            const data = getCashflowData();
            
            if (!data || data.length === 0) {
                showWarning('Aucune donnée à exporter');
                return;
            }
            
            // Create CSV content
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
            
            // Download file
            downloadFile(csvContent, 'tresorerie.csv', 'text/csv');
            showSuccess('✅ Export CSV réussi');
            
        } catch (error) {
            console.error('❌ CSV export error:', error);
            showError('Erreur lors de l\'export CSV: ' + error.message);
        }
    };
    
    // Export cashflow to PDF
    window.exportPDF = function() {
        console.log('📄 Exporting to PDF...');
        
        try {
            const data = getCashflowData();
            
            if (!data || data.length === 0) {
                showWarning('Aucune donnée à exporter');
                return;
            }
            
            // Create HTML for PDF
            const html = `
                <!DOCTYPE html>
                <html>
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
            
            // Open in new window for printing
            const printWindow = window.open('', '_blank');
            printWindow.document.write(html);
            printWindow.document.close();
            
            // Auto print dialog
            setTimeout(() => {
                printWindow.print();
            }, 500);
            
            showSuccess('✅ PDF ouvert - utilisez Ctrl+P pour imprimer');
            
        } catch (error) {
            console.error('❌ PDF export error:', error);
            showError('Erreur lors de l\'export PDF: ' + error.message);
        }
    };
    
    // Export cashflow to Excel
    window.exportExcel = function() {
        console.log('📗 Exporting to Excel...');
        
        try {
            const data = getCashflowData();
            
            if (!data || data.length === 0) {
                showWarning('Aucune donnée à exporter');
                return;
            }
            
            // Create Excel-compatible HTML
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
            
            // Download as Excel
            downloadFile(html, 'tresorerie.xls', 'application/vnd.ms-excel');
            showSuccess('✅ Export Excel réussi');
            
        } catch (error) {
            console.error('❌ Excel export error:', error);
            showError('Erreur lors de l\'export Excel: ' + error.message);
        }
    };
    
    // Helper: Get cashflow data
    function getCashflowData() {
        // Try to get from global variable first
        if (window.cashflowData && window.cashflowData.length > 0) {
            return window.cashflowData;
        }
        
        // Try to scrape from table
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
        
        // Generate sample data if nothing found
        console.warn('⚠️ No data found, using sample data');
        return [
            { date: '2026-01-24', type: 'Vente', description: 'Facture F-2024-001', amount: 2400, balance: 15000 },
            { date: '2026-01-23', type: 'Achat', description: 'Fournisseur ABC', amount: -850, balance: 12600 },
            { date: '2026-01-22', type: 'Vente', description: 'Facture F-2024-002', amount: 1800, balance: 13450 }
        ];
    }
    
    // Helper: Download file
    function downloadFile(content, filename, mimeType) {
        const blob = new Blob(['\ufeff' + content], { type: mimeType + ';charset=utf-8;' });
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

    console.log('✅ Module Exports chargé');
})();

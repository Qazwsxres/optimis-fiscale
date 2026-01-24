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

    console.log('✅ Module Exports chargé');
})();

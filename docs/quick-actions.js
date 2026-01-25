/**
 * NUMMA Quick Actions Module
 * Handles dashboard quick actions: Generate Report, Contact Expert, Plan Optimization
 */

(function() {
    'use strict';

    /**
     * Generate complete report
     */
    window.generateReport = function() {
        console.log('📊 Generating complete report...');
        
        showInfo('⏳ Génération du rapport en cours...');
        
        try {
            // Collect data
            const reportData = collectReportData();
            
            // Create report HTML
            const html = createReportHTML(reportData);
            
            // Open in new window
            const reportWindow = window.open('', '_blank');
            reportWindow.document.write(html);
            reportWindow.document.close();
            
            showSuccess('✅ Rapport généré avec succès');
            
        } catch (error) {
            console.error('❌ Report generation error:', error);
            showError('Erreur lors de la génération du rapport: ' + error.message);
        }
    };
    
    /**
     * Contact expert - improved version
     */
    window.contactExpert = function() {
        console.log('👤 Opening contact expert...');
        
        const email = 'expert@numma.fr';
        const subject = 'Demande de conseil - NUMMA';
        const body = `Bonjour,

Je souhaite obtenir des conseils concernant ma gestion financière.

Cordialement`;
        
        const mailtoLink = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        
        window.location.href = mailtoLink;
        showInfo('📧 Ouverture de votre client mail...');
    };
    
    /**
     * Plan optimization - improved version
     */
    window.planOptimization = function() {
        console.log('📈 Planning optimization...');
        
        showInfo('⏳ Analyse en cours...');
        
        setTimeout(() => {
            const recommendations = getOptimizationRecommendations();
            showOptimizationModal(recommendations);
        }, 1000);
    };
    
    // =====================================================
    // HELPER FUNCTIONS
    // =====================================================
    
    /**
     * Collect all data for report
     */
    function collectReportData() {
        return {
            generatedAt: new Date().toLocaleString('fr-FR'),
            company: 'NUMMA SAS',
            
            // Financial summary
            cashflow: {
                current: getCurrentBalance(),
                incoming: getIncomingPayments(),
                outgoing: getOutgoingPayments(),
                net: getNetCashflow()
            },
            
            // Invoices
            invoices: {
                total: getTotalInvoices(),
                paid: getPaidInvoices(),
                pending: getPendingInvoices(),
                overdue: getOverdueInvoices()
            },
            
            // Alerts
            alerts: getActiveAlerts()
        };
    }
    
    /**
     * Create report HTML
     */
    function createReportHTML(data) {
        return `
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Complet NUMMA - ${data.generatedAt}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .content { padding: 40px; }
        .section {
            margin-bottom: 40px;
            border-left: 4px solid #2563eb;
            padding-left: 20px;
        }
        .section h2 {
            color: #1e40af;
            font-size: 1.8rem;
            margin-bottom: 20px;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .metric-card {
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 24px;
            transition: all 0.3s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(37,99,235,0.2);
        }
        .metric-label {
            font-size: 0.9rem;
            color: #64748b;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #1e293b;
        }
        .metric-value.positive { color: #10b981; }
        .metric-value.negative { color: #ef4444; }
        .metric-value.warning { color: #f59e0b; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background: #f1f5f9;
            color: #1e40af;
            font-weight: 600;
        }
        tr:hover { background: #f8fafc; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .badge.success { background: #d1fae5; color: #065f46; }
        .badge.warning { background: #fef3c7; color: #92400e; }
        .badge.error { background: #fee2e2; color: #991b1b; }
        .footer {
            background: #f8fafc;
            padding: 30px;
            text-align: center;
            border-top: 2px solid #e2e8f0;
        }
        @media print {
            body { background: white; padding: 0; }
            .container { box-shadow: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Rapport Complet NUMMA</h1>
            <p>${data.company}</p>
            <p>Généré le ${data.generatedAt}</p>
        </div>
        
        <div class="content">
            <!-- Trésorerie -->
            <div class="section">
                <h2>💰 Trésorerie</h2>
                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-label">Solde actuel</div>
                        <div class="metric-value">${data.cashflow.current.toLocaleString('fr-FR')} €</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Encaissements à venir</div>
                        <div class="metric-value positive">+${data.cashflow.incoming.toLocaleString('fr-FR')} €</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Décaissements prévus</div>
                        <div class="metric-value negative">-${data.cashflow.outgoing.toLocaleString('fr-FR')} €</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Flux net</div>
                        <div class="metric-value ${data.cashflow.net >= 0 ? 'positive' : 'negative'}">
                            ${data.cashflow.net.toLocaleString('fr-FR')} €
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Factures -->
            <div class="section">
                <h2>📄 Factures</h2>
                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-label">Total factures</div>
                        <div class="metric-value">${data.invoices.total}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Payées</div>
                        <div class="metric-value positive">${data.invoices.paid}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">En attente</div>
                        <div class="metric-value warning">${data.invoices.pending}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">En retard</div>
                        <div class="metric-value negative">${data.invoices.overdue}</div>
                    </div>
                </div>
            </div>
            
            <!-- Alertes -->
            <div class="section">
                <h2>🔔 Alertes actives</h2>
                ${data.alerts.length > 0 ? `
                    <table>
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Message</th>
                                <th>Priorité</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.alerts.map(alert => `
                                <tr>
                                    <td>${alert.type}</td>
                                    <td>${alert.message}</td>
                                    <td><span class="badge ${alert.priority}">${alert.priority}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p style="color: #10b981; font-weight: 500;">✅ Aucune alerte active</p>'}
            </div>
        </div>
        
        <div class="footer">
            <p><strong>NUMMA</strong> - Gestion financière intelligente</p>
            <p style="margin-top: 10px; color: #64748b;">Ce rapport a été généré automatiquement</p>
        </div>
    </div>
</body>
</html>
        `;
    }
    
    /**
     * Get optimization recommendations
     */
    function getOptimizationRecommendations() {
        return [
            { icon: '💰', title: 'Optimiser la trésorerie', desc: 'Améliorer vos délais de paiement', impact: 'high' },
            { icon: '📊', title: 'Réduire les coûts', desc: 'Identifier les dépenses non essentielles', impact: 'medium' },
            { icon: '📈', title: 'Augmenter les revenus', desc: 'Stratégies de croissance', impact: 'high' },
            { icon: '🎯', title: 'Automatiser les processus', desc: 'Gagner du temps sur les tâches répétitives', impact: 'medium' }
        ];
    }
    
    /**
     * Show optimization modal
     */
    function showOptimizationModal(recommendations) {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7); display: flex; align-items: center;
            justify-content: center; z-index: 10000; animation: fadeIn 0.3s;
        `;
        
        modal.innerHTML = `
            <div style="background: white; border-radius: 20px; padding: 40px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;">
                <h2 style="color: #2563eb; margin-bottom: 20px;">📈 Plan d'Optimisation</h2>
                <p style="color: #64748b; margin-bottom: 30px;">Recommandations personnalisées pour améliorer votre gestion</p>
                
                ${recommendations.map(rec => `
                    <div style="background: #f8fafc; border-left: 4px solid ${rec.impact === 'high' ? '#10b981' : '#f59e0b'}; padding: 20px; margin-bottom: 15px; border-radius: 8px;">
                        <div style="font-size: 2rem; margin-bottom: 10px;">${rec.icon}</div>
                        <h3 style="color: #1e40af; margin-bottom: 8px;">${rec.title}</h3>
                        <p style="color: #64748b;">${rec.desc}</p>
                        <span style="display: inline-block; margin-top: 10px; padding: 4px 12px; background: ${rec.impact === 'high' ? '#d1fae5' : '#fef3c7'}; color: ${rec.impact === 'high' ? '#065f46' : '#92400e'}; border-radius: 999px; font-size: 0.85rem;">
                            Impact ${rec.impact === 'high' ? 'élevé' : 'moyen'}
                        </span>
                    </div>
                `).join('')}
                
                <button onclick="this.parentElement.parentElement.remove()" style="width: 100%; padding: 15px; background: #2563eb; color: white; border: none; border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer; margin-top: 20px;">
                    Fermer
                </button>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
    }
    
    // Helper functions to get data
    function getCurrentBalance() { return 25450; }
    function getIncomingPayments() { return 8750; }
    function getOutgoingPayments() { return 3200; }
    function getNetCashflow() { return 5550; }
    function getTotalInvoices() { return 47; }
    function getPaidInvoices() { return 32; }
    function getPendingInvoices() { return 12; }
    function getOverdueInvoices() { return 3; }
    function getActiveAlerts() {
        return [
            { type: 'Paiement', message: 'Facture F-2024-003 en retard', priority: 'error' },
            { type: 'Trésorerie', message: 'Solde faible prévu dans 15 jours', priority: 'warning' }
        ];
    }
    
    console.log('✅ Module Quick Actions chargé');
})();

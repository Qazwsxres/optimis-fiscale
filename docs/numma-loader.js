/**
 * ========================================
 * NUMMA - LOADER PRINCIPAL v3.0
 * ========================================
 * 
 * Charge tous les modules dans le bon ordre
 * Vérifie les dépendances
 * Configure l'application
 */

console.log('%c========================================', 'color: #2563eb; font-weight: bold');
console.log('%c NUMMA Dashboard - Chargement des modules', 'color: #2563eb; font-weight: bold');
console.log('%c========================================', 'color: #2563eb; font-weight: bold');

// =====================================================
// CONFIGURATION GLOBALE CENTRALISÉE
// =====================================================

window.NUMMA_CONFIG = {
    VERSION: '3.0.0',
    API_BASE: 'https://optimis-fiscale-production.up.railway.app',
    MODULES: {
        messages: false,      // numma-messages.js
        interactive: false,   // numma-interactive-complete.js
        invoices: false,      // numma-invoices.js
        employees: false,     // numma-employees.js
        imports: false,       // numma-imports.js
        exports: false,       // numma-exports.js
        pointages: false      // numma-pointages.js
    },
    FEATURES: {
        backend: true,
        ocr: true,
        exports_pdf: true,
        exports_excel: true,
        auto_sync: true
    }
};

// =====================================================
// VÉRIFICATION DES DÉPENDANCES
// =====================================================

/**
 * Vérifie qu'un module est chargé
 */
function checkModule(moduleName, globalVar) {
    if (typeof window[globalVar] !== 'undefined') {
        NUMMA_CONFIG.MODULES[moduleName] = true;
        console.log(`✅ Module ${moduleName} chargé`);
        return true;
    } else {
        console.warn(`⚠️ Module ${moduleName} non chargé (${globalVar} non défini)`);
        return false;
    }
}

/**
 * Vérifie toutes les dépendances
 */
function checkAllDependencies() {
    console.log('🔍 Vérification des dépendances...');
    
    // Vérifier numma-messages.js (REQUIS)
    if (!checkModule('messages', 'showMessage')) {
        console.error('❌ ERREUR CRITIQUE: numma-messages.js doit être chargé EN PREMIER');
        alert('❌ Erreur: Système de messages non chargé. Veuillez rafraîchir la page.');
        return false;
    }
    
    // Vérifier numma-interactive-complete.js (OPTIONNEL)
    checkModule('interactive', 'makeChartInteractive');
    
    // Vérifier les modules optionnels
    checkModule('invoices', 'invoiceAPI');
    checkModule('employees', 'employeeAPI');
    checkModule('imports', 'importAPI');
    checkModule('exports', 'exportCSV');
    checkModule('pointages', 'pointageAPI');
    
    return true;
}

// =====================================================
// INITIALISATION DES MODULES
// =====================================================

/**
 * Initialise tous les modules chargés
 */
async function initializeModules() {
    console.log('🚀 Initialisation des modules...');
    
    try {
        // Factures
        if (NUMMA_CONFIG.MODULES.invoices && typeof loadInvoices === 'function') {
            console.log('📄 Initialisation module Factures...');
            // Auto-load si on est sur la vue factures
            if (document.getElementById('viewFactures')) {
                setTimeout(() => loadInvoices().catch(console.error), 500);
            }
        }
        
        // Employés
        if (NUMMA_CONFIG.MODULES.employees && typeof loadEmployees === 'function') {
            console.log('👥 Initialisation module Employés...');
            if (document.getElementById('viewRH')) {
                setTimeout(() => loadEmployees().catch(console.error), 500);
            }
        }
        
        // Imports
        if (NUMMA_CONFIG.MODULES.imports && typeof initializeDropZones === 'function') {
            console.log('📁 Initialisation module Imports...');
            initializeDropZones();
        }
        
        // Exports
        if (NUMMA_CONFIG.MODULES.exports) {
            console.log('📥 Module Exports disponible');
        }
        
        // Pointages
        if (NUMMA_CONFIG.MODULES.pointages) {
            console.log('⏰ Initialisation module Pointages...');
            if (typeof pointageAPI !== 'undefined' && NUMMA_CONFIG.FEATURES.auto_sync) {
                pointageAPI.startAutoSync();
            }
            if (document.getElementById('viewPointage')) {
                setTimeout(() => {
                    if (typeof updateClockHistoryTable === 'function') {
                        updateClockHistoryTable();
                    }
                    if (typeof updateClockStats === 'function') {
                        updateClockStats();
                    }
                }, 500);
            }
        }
        
        console.log('✅ Tous les modules initialisés');
        
    } catch (error) {
        console.error('❌ Erreur initialisation modules:', error);
        showError('Erreur lors de l\'initialisation: ' + error.message);
    }
}

// =====================================================
// GESTION DE LA CONNEXION
// =====================================================

/**
 * Vérifie le token d'authentification
 */
function checkAuth() {
    const token = localStorage.getItem('authToken');
    
    if (!token) {
        console.warn('⚠️ Aucun token d\'authentification');
        console.log('🔄 Redirection vers login...');
        // Uncomment in production:
        // window.location.href = 'login.html';
        return false;
    }
    
    console.log('✅ Token d\'authentification trouvé');
    return true;
}

/**
 * Initialise les infos utilisateur
 */
function initializeUserInfo() {
    const userData = JSON.parse(localStorage.getItem('currentUser') || '{}');
    
    // Mettre à jour l'affichage
    const userNameEl = document.getElementById('userName');
    if (userNameEl) {
        userNameEl.textContent = userData.contact_name || userData.name || 'Utilisateur';
    }
    
    const userCompanyEl = document.getElementById('userCompany');
    if (userCompanyEl) {
        userCompanyEl.textContent = userData.company_name || 'Entreprise';
    }
    
    const userAccessEl = document.getElementById('userAccessLevel');
    if (userAccessEl) {
        userAccessEl.textContent = userData.accessLevel || 'Admin';
    }
    
    console.log('👤 Utilisateur:', userData.contact_name || 'N/A');
    console.log('🏢 Entreprise:', userData.company_name || 'N/A');
}

// =====================================================
// HELPERS GLOBAUX
// =====================================================

/**
 * Teste la connexion au backend
 */
async function testBackendConnection() {
    try {
        const response = await fetch(`${NUMMA_CONFIG.API_BASE}/health`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('authToken')}`
            }
        });
        
        if (response.ok) {
            console.log('✅ Backend accessible');
            return true;
        } else {
            console.warn('⚠️ Backend inaccessible (status:', response.status + ')');
            return false;
        }
    } catch (error) {
        console.warn('⚠️ Backend hors ligne:', error.message);
        return false;
    }
}

/**
 * Affiche le statut de l'application
 */
function displayAppStatus() {
    const loadedModules = Object.entries(NUMMA_CONFIG.MODULES)
        .filter(([_, loaded]) => loaded)
        .map(([name, _]) => name);
    
    const enabledFeatures = Object.entries(NUMMA_CONFIG.FEATURES)
        .filter(([_, enabled]) => enabled)
        .map(([name, _]) => name);
    
    console.log('%c NUMMA Dashboard Ready! ', 'background: #2563eb; color: white; font-size: 14px; padding: 5px;');
    console.log('📦 Version:', NUMMA_CONFIG.VERSION);
    console.log('✅ Modules chargés:', loadedModules.join(', ') || 'aucun');
    console.log('🎯 Fonctionnalités:', enabledFeatures.join(', '));
    console.log('');
}

// =====================================================
// DÉMARRAGE AUTOMATIQUE
// =====================================================

/**
 * Initialise l'application
 */
async function startNumma() {
    console.log('🚀 Démarrage NUMMA...');
    
    // 1. Vérifier les dépendances
    if (!checkAllDependencies()) {
        console.error('❌ Dépendances manquantes - Arrêt');
        return;
    }
    
    // 2. Vérifier l'authentification
    checkAuth();
    
    // 3. Initialiser les infos utilisateur
    initializeUserInfo();
    
    // 4. Tester le backend
    const backendOk = await testBackendConnection();
    
    if (!backendOk) {
        showWarning('Mode hors ligne - Utilisation des données locales');
    }
    
    // 5. Initialiser les modules
    await initializeModules();
    
    // 6. Afficher le statut
    displayAppStatus();
    
    // 7. Message de bienvenue
    setTimeout(() => {
        showSuccess('NUMMA prêt - Tous les modules sont chargés');
    }, 1000);
}

// Démarrer au chargement de la page
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startNumma);
} else {
    startNumma();
}

// =====================================================
// EXPORT GLOBAL
// =====================================================

window.NUMMA = {
    config: NUMMA_CONFIG,
    checkDependencies: checkAllDependencies,
    testBackend: testBackendConnection,
    restart: startNumma
};

console.log('✅ NUMMA Loader chargé');

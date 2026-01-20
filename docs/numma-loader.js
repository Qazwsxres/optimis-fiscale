/**
 * ========================================
 * NUMMA - LOADER PRINCIPAL
 * ========================================
 * 
 * Charge tous les modules dans le bon ordre
 * Vérifie les dépendances
 * Configure l'application
 * 
 * Modules chargés:
 * 1. Factures (numma-invoices.js)
 * 2. Employés & Paie (numma-employees.js)
 * 3. Imports avec OCR (numma-imports.js)
 * 4. Exports (CSV, PDF, Excel) (numma-exports.js)
 * 5. Pointages synchronisés (numma-pointages.js)
 */

console.log('%c========================================', 'color: #2563eb; font-weight: bold');
console.log('%c NUMMA Dashboard - Chargement des modules', 'color: #2563eb; font-weight: bold');
console.log('%c========================================', 'color: #2563eb; font-weight: bold');

// =====================================================
// CONFIGURATION GLOBALE
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
        console.warn(`⚠️ Module ${moduleName} non chargé`);
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
        console.error('❌ ERREUR: numma-messages.js doit être chargé EN PREMIER');
        return false;
    }
    
    // Vérifier numma-interactive-complete.js (REQUIS)
    if (!checkModule('interactive', 'notify')) {
        console.warn('⚠️ numma-interactive-complete.js non chargé - fonctionnalités limitées');
    }
    
    // Vérifier les modules optionnels
    checkModule('invoices', 'invoiceAPI');
    checkModule('employees', 'employeeAPI');
    checkModule('imports', 'importAPI');
    checkModule('exports', 'exportAPI');
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
        if (NUMMA_CONFIG.MODULES.invoices) {
            console.log('📄 Initialisation module Factures...');
            // Auto-load factures si on est sur la vue
            if (document.getElementById('viewFactures')) {
                setTimeout(() => {
                    if (typeof loadInvoices === 'function') {
                        loadInvoices();
                    }
                }, 500);
            }
        }
        
        // Employés
        if (NUMMA_CONFIG.MODULES.employees) {
            console.log('👥 Initialisation module Employés...');
            if (document.getElementById('viewRH')) {
                setTimeout(() => {
                    if (typeof loadEmployees === 'function') {
                        loadEmployees();
                    }
                }, 500);
            }
        }
        
        // Imports
        if (NUMMA_CONFIG.MODULES.imports) {
            console.log('📁 Initialisation module Imports...');
            // Les zones de drop sont initialisées automatiquement
        }
        
        // Exports
        if (NUMMA_CONFIG.MODULES.exports) {
            console.log('📥 Initialisation module Exports...');
            // Exports sont disponibles à la demande
        }
        
        // Pointages
        if (NUMMA_CONFIG.MODULES.pointages) {
            console.log('⏰ Initialisation module Pointages...');
            // Auto-sync démarré automatiquement
            if (document.getElementById('viewPointage')) {
                setTimeout(() => {
                    if (typeof updateClockHistoryTable === 'function') {
                        updateClockHistoryTable();
                        updateClockStats();
                    }
                }, 500);
            }
        }
        
        console.log('✅ Tous les modules initialisés');
        
    } catch (error) {
        console.error('❌ Erreur initialisation modules:', error);
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
        // Créer un token demo
        localStorage.setItem('authToken', 'demo-token');
        console.log('✅ Token demo créé');
    }
    
    return true;
}

/**
 * Initialise les infos utilisateur
 */
function initializeUserInfo() {
    const userData = JSON.parse(localStorage.getItem('currentUser') || '{}');
    
    // Mettre à jour l'affichage
    if (document.getElementById('userName')) {
        document.getElementById('userName').textContent = 
            userData.name || 'Utilisateur';
    }
    
    if (document.getElementById('userCompany')) {
        document.getElementById('userCompany').textContent = 
            userData.company_name || 'Entreprise';
    }
    
    if (document.getElementById('userAccessLevel')) {
        document.getElementById('userAccessLevel').textContent = 
            userData.access_level || 'Admin';
    }
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
            console.warn('⚠️ Backend inaccessible');
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
    const status = {
        version: NUMMA_CONFIG.VERSION,
        modules: Object.entries(NUMMA_CONFIG.MODULES)
            .filter(([_, loaded]) => loaded)
            .map(([name, _]) => name),
        features: Object.entries(NUMMA_CONFIG.FEATURES)
            .filter(([_, enabled]) => enabled)
            .map(([name, _]) => name)
    };
    
    console.log('%c NUMMA Dashboard Ready! ', 'background: #2563eb; color: white; font-size: 14px; padding: 5px;');
    console.log('Version:', status.version);
    console.log('Modules chargés:', status.modules.join(', '));
    console.log('Fonctionnalités:', status.features.join(', '));
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
        showWarning('Mode hors ligne', 
            'Backend inaccessible. Utilisation des données locales.');
    }
    
    // 5. Initialiser les modules
    await initializeModules();
    
    // 6. Afficher le statut
    displayAppStatus();
    
    // 7. Afficher un message de bienvenue
    if (typeof showSuccess === 'function') {
        setTimeout(() => {
            showSuccess('NUMMA prêt', 'Tous les modules sont chargés');
        }, 1000);
    }
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

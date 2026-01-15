/**
 * Module FEC (Fichier des Écritures Comptables)
 * Conforme à l'Article A47 A-1 du Livre des Procédures Fiscales (LPF)
 * 
 * Exigences:
 * - Encodage: ASCII ou ISO 8859-1 (pas UTF-8)
 * - Séparateur: Pipe (|) ou Tabulation
 * - 18 champs obligatoires dans l'ordre précis
 * - Intangibilité des écritures validées (ValidDate non vide)
 */

class FECManager {
    constructor() {
        // Configuration FEC
        this.SEPARATOR = '|'; // Pipe separator (can be changed to \t for tab)
        this.ENCODING = 'ISO-8859-1'; // Required encoding
        
        // Storage key
        this.STORAGE_KEY = 'numma_fec_entries';
        
        // Field definitions (18 mandatory fields)
        this.FIELDS = [
            'JournalCode',      // Code journal (ex: VE pour ventes)
            'JournalLib',       // Libellé journal
            'EcritureNum',      // Numéro de séquence unique
            'EcritureDate',     // Date comptabilisation (YYYYMMDD)
            'CompteNum',        // Numéro de compte (PCG)
            'CompteLib',        // Libellé du compte
            'CompAuxNum',       // Compte auxiliaire (client/fournisseur)
            'CompAuxLib',       // Libellé auxiliaire
            'PieceRef',         // Référence pièce justificative
            'PieceDate',        // Date de la pièce (YYYYMMDD)
            'EcritureLib',      // Libellé de l'écriture
            'Debit',            // Montant débit (format: 0.00)
            'Credit',           // Montant crédit (format: 0.00)
            'EcritureLet',      // Lettrage (vide ou code)
            'DateLet',          // Date lettrage (YYYYMMDD ou vide)
            'ValidDate',        // Date validation définitive (YYYYMMDD)
            'Montantdevise',    // Montant en devise (vide si EUR)
            'Idevise',          // Code devise (vide si EUR)
        ];
    }

    /**
     * Get all FEC entries from localStorage
     */
    getEntries() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (error) {
            console.error('Error loading FEC entries:', error);
            return [];
        }
    }

    /**
     * Save FEC entries to localStorage
     */
    saveEntries(entries) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(entries));
            return true;
        } catch (error) {
            console.error('Error saving FEC entries:', error);
            return false;
        }
    }

    /**
     * Add a new accounting entry
     * Returns: {success: boolean, error?: string, entry?: object}
     */
    addEntry(entry) {
        // Validate entry
        const validation = this.validateEntry(entry);
        if (!validation.valid) {
            return { success: false, error: validation.error };
        }

        const entries = this.getEntries();
        
        // Generate unique EcritureNum if not provided
        if (!entry.EcritureNum) {
            entry.EcritureNum = this.generateEcritureNum(entries);
        }

        // Check if EcritureNum is unique
        if (entries.find(e => e.EcritureNum === entry.EcritureNum)) {
            return { success: false, error: 'EcritureNum must be unique' };
        }

        // Add entry
        entries.push(entry);
        
        if (this.saveEntries(entries)) {
            return { success: true, entry };
        } else {
            return { success: false, error: 'Failed to save entry' };
        }
    }

    /**
     * Update an existing entry
     * CRITICAL: Cannot modify if entry has ValidDate (intangibilité)
     */
    updateEntry(ecritureNum, updates) {
        const entries = this.getEntries();
        const index = entries.findIndex(e => e.EcritureNum === ecritureNum);
        
        if (index === -1) {
            return { success: false, error: 'Entry not found' };
        }

        const entry = entries[index];

        // INTANGIBILITÉ: Cannot modify validated entries
        if (entry.ValidDate && entry.ValidDate.trim() !== '') {
            return { 
                success: false, 
                error: 'INTANGIBILITÉ: Cannot modify a validated entry (ValidDate is set)' 
            };
        }

        // Apply updates
        Object.assign(entry, updates);

        // Validate updated entry
        const validation = this.validateEntry(entry);
        if (!validation.valid) {
            return { success: false, error: validation.error };
        }

        entries[index] = entry;
        
        if (this.saveEntries(entries)) {
            return { success: true, entry };
        } else {
            return { success: false, error: 'Failed to save entry' };
        }
    }

    /**
     * Validate entry (must have ValidDate to be final)
     */
    validateEntry(entry) {
        const dateFormat = /^\d{8}$/; // YYYYMMDD
        const amountFormat = /^\d+(\.\d{1,2})?$/; // 0.00 format

        // Check mandatory fields
        const requiredFields = [
            'JournalCode', 'JournalLib', 'EcritureNum', 'EcritureDate',
            'CompteNum', 'CompteLib', 'PieceRef', 'PieceDate', 'EcritureLib'
        ];

        for (const field of requiredFields) {
            if (!entry[field] || entry[field].toString().trim() === '') {
                return { valid: false, error: `Field ${field} is required` };
            }
        }

        // Validate date formats
        if (!dateFormat.test(entry.EcritureDate)) {
            return { valid: false, error: 'EcritureDate must be YYYYMMDD format' };
        }
        if (!dateFormat.test(entry.PieceDate)) {
            return { valid: false, error: 'PieceDate must be YYYYMMDD format' };
        }
        if (entry.ValidDate && !dateFormat.test(entry.ValidDate)) {
            return { valid: false, error: 'ValidDate must be YYYYMMDD format or empty' };
        }
        if (entry.DateLet && entry.DateLet.trim() !== '' && !dateFormat.test(entry.DateLet)) {
            return { valid: false, error: 'DateLet must be YYYYMMDD format or empty' };
        }

        // Validate amounts (must be one of Debit or Credit, not both)
        const debit = parseFloat(entry.Debit || '0');
        const credit = parseFloat(entry.Credit || '0');

        if (debit < 0 || credit < 0) {
            return { valid: false, error: 'Debit and Credit must be positive' };
        }

        if (debit > 0 && credit > 0) {
            return { valid: false, error: 'Cannot have both Debit and Credit' };
        }

        if (debit === 0 && credit === 0) {
            return { valid: false, error: 'Must have either Debit or Credit' };
        }

        return { valid: true };
    }

    /**
     * Generate unique EcritureNum
     */
    generateEcritureNum(entries) {
        const year = new Date().getFullYear();
        const existing = entries.filter(e => e.EcritureNum.startsWith(year.toString()));
        const nextNum = existing.length + 1;
        return `${year}${nextNum.toString().padStart(6, '0')}`;
    }

    /**
     * Format value for FEC export (handle special characters)
     */
    formatValue(value) {
        if (value === null || value === undefined) {
            return '';
        }
        
        const str = value.toString().trim();
        
        // Replace problematic characters for ISO-8859-1
        return str
            .replace(/[€]/g, 'EUR') // Euro symbol not in ISO-8859-1
            .replace(/[\u0080-\uFFFF]/g, '') // Remove non-ASCII chars
            .replace(/\r?\n/g, ' ') // Replace line breaks
            .replace(/\t/g, ' '); // Replace tabs
    }

    /**
     * Export FEC to TXT file (ISO-8859-1 encoded)
     * @param {number} year - Fiscal year (optional, exports all if not specified)
     * @param {boolean} onlyValidated - Export only validated entries
     */
    exportFEC(year = null, onlyValidated = false) {
        let entries = this.getEntries();

        // Filter by year if specified
        if (year) {
            const yearStr = year.toString();
            entries = entries.filter(e => e.EcritureDate.startsWith(yearStr));
        }

        // Filter only validated if requested
        if (onlyValidated) {
            entries = entries.filter(e => e.ValidDate && e.ValidDate.trim() !== '');
        }

        if (entries.length === 0) {
            return { success: false, error: 'No entries to export' };
        }

        // Sort by EcritureDate, then EcritureNum
        entries.sort((a, b) => {
            if (a.EcritureDate !== b.EcritureDate) {
                return a.EcritureDate.localeCompare(b.EcritureDate);
            }
            return a.EcritureNum.localeCompare(b.EcritureNum);
        });

        // Build FEC content
        let fecContent = '';

        // Header line (field names)
        fecContent += this.FIELDS.join(this.SEPARATOR) + '\n';

        // Data lines
        for (const entry of entries) {
            const line = this.FIELDS.map(field => {
                let value = entry[field] || '';
                
                // Format amounts with 2 decimals
                if (field === 'Debit' || field === 'Credit' || field === 'Montantdevise') {
                    const num = parseFloat(value || '0');
                    value = num.toFixed(2);
                }
                
                return this.formatValue(value);
            }).join(this.SEPARATOR);
            
            fecContent += line + '\n';
        }

        // Generate filename
        const companyData = JSON.parse(localStorage.getItem('currentUser') || '{}');
        const siret = companyData.siret || 'SIRET';
        const fiscalYear = year || new Date().getFullYear();
        const filename = `${siret}FEC${fiscalYear}.txt`;

        return {
            success: true,
            content: fecContent,
            filename: filename,
            encoding: this.ENCODING,
            entriesCount: entries.length
        };
    }

    /**
     * Download FEC file
     */
    downloadFEC(year = null, onlyValidated = false) {
        const result = this.exportFEC(year, onlyValidated);
        
        if (!result.success) {
            alert('Erreur: ' + result.error);
            return false;
        }

        // Create blob with ISO-8859-1 encoding
        // Note: Modern browsers may not fully support ISO-8859-1, 
        // so we ensure ASCII-compatible content
        const blob = new Blob([result.content], { 
            type: 'text/plain;charset=ISO-8859-1' 
        });

        // Create download link
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = result.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        alert(`✅ FEC exporté!\n\nFichier: ${result.filename}\nÉcritures: ${result.entriesCount}\nEncodage: ${result.encoding}`);
        return true;
    }

    /**
     * Get statistics
     */
    getStats() {
        const entries = this.getEntries();
        
        const validated = entries.filter(e => e.ValidDate && e.ValidDate.trim() !== '');
        const notValidated = entries.filter(e => !e.ValidDate || e.ValidDate.trim() === '');
        
        const totalDebit = entries.reduce((sum, e) => sum + parseFloat(e.Debit || '0'), 0);
        const totalCredit = entries.reduce((sum, e) => sum + parseFloat(e.Credit || '0'), 0);

        return {
            total: entries.length,
            validated: validated.length,
            notValidated: notValidated.length,
            totalDebit: totalDebit.toFixed(2),
            totalCredit: totalCredit.toFixed(2),
            balanced: Math.abs(totalDebit - totalCredit) < 0.01
        };
    }
}

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.FECManager = FECManager;
}

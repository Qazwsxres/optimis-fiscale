/**
 * NUMMA Interactive Complete
 * Enhanced interactive features for charts and data visualization
 */

(function() {
    'use strict';

    /**
     * Make chart interactive with tooltips and click events
     */
    window.makeChartInteractive = function(chartId, data) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;

        canvas.addEventListener('mousemove', function(e) {
            // Get mouse position relative to canvas
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Show tooltip if hovering over data point
            // Implementation depends on chart library
        });

        canvas.addEventListener('click', function(e) {
            // Handle click on data point
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Trigger custom event
            canvas.dispatchEvent(new CustomEvent('chartClick', { 
                detail: { x, y, data } 
            }));
        });
    };

    /**
     * Add zoom functionality to charts
     */
    window.addChartZoom = function(chartId) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;

        let scale = 1;

        canvas.addEventListener('wheel', function(e) {
            e.preventDefault();
            
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            scale *= delta;
            
            // Limit scale
            scale = Math.max(0.5, Math.min(3, scale));
            
            canvas.style.transform = `scale(${scale})`;
        });
    };

    /**
     * Enable pan functionality
     */
    window.addChartPan = function(chartId) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;

        let isPanning = false;
        let startX, startY;
        let translateX = 0, translateY = 0;

        canvas.addEventListener('mousedown', function(e) {
            isPanning = true;
            startX = e.clientX - translateX;
            startY = e.clientY - translateY;
            canvas.style.cursor = 'grabbing';
        });

        document.addEventListener('mousemove', function(e) {
            if (!isPanning) return;
            
            translateX = e.clientX - startX;
            translateY = e.clientY - startY;
            
            canvas.style.transform = `translate(${translateX}px, ${translateY}px)`;
        });

        document.addEventListener('mouseup', function() {
            if (!isPanning) return;
            isPanning = false;
            canvas.style.cursor = 'grab';
        });
    };

    /**
     * Animate chart on load
     */
    window.animateChart = function(chartId, duration = 1000) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;

        canvas.style.opacity = '0';
        canvas.style.transition = `opacity ${duration}ms ease`;
        
        setTimeout(() => {
            canvas.style.opacity = '1';
        }, 100);
    };

    /**
     * Export chart as image
     */
    window.exportChart = function(chartId, filename = 'chart.png') {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;

        // Create download link
        const link = document.createElement('a');
        link.download = filename;
        link.href = canvas.toDataURL('image/png');
        link.click();
    };

    /**
     * Toggle chart legend
     */
    window.toggleChartLegend = function(chartId) {
        const legend = document.querySelector(`#${chartId} + .chart-legend`);
        if (!legend) return;

        legend.style.display = legend.style.display === 'none' ? 'block' : 'none';
    };

    /**
     * Refresh chart data
     */
    window.refreshChart = function(chartId, newData) {
        // Trigger chart update event
        const canvas = document.getElementById(chartId);
        if (!canvas) return;

        canvas.dispatchEvent(new CustomEvent('chartUpdate', {
            detail: { data: newData }
        }));
    };

    console.log('✅ NUMMA Interactive Complete loaded');
})();

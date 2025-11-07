/**
 * Company Notes and Salesperson Assignment Component
 */

function openNotesModal(companyId, companyName, currentNotes = '', currentSalesperson = '') {
    const modal = document.getElementById('notesModal') || createNotesModal();
    
    document.getElementById('notesModalTitle').textContent = `Notes: ${companyName}`;
    document.getElementById('notesCompanyId').value = companyId;
    document.getElementById('notesTextarea').value = currentNotes || '';
    document.getElementById('salespersonInput').value = currentSalesperson || '';
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

function createNotesModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'notesModal';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="notesModalTitle">Company Notes</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="hidden" id="notesCompanyId">
                    
                    <div class="mb-3">
                        <label class="form-label fw-bold">
                            <i class="fas fa-user-tie me-2"></i>Assigned Salesperson
                        </label>
                        <input type="text" class="form-control" id="salespersonInput" 
                               placeholder="Enter your name...">
                        <small class="text-muted">Assign yourself or a team member to this company</small>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label fw-bold">
                            <i class="fas fa-sticky-note me-2"></i>Notes
                        </label>
                        <textarea class="form-control" id="notesTextarea" rows="8" 
                                  placeholder="Add notes about this company..."></textarea>
                        <small class="text-muted">Track conversations, preferences, opportunities, etc.</small>
                    </div>
                    
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-info-circle me-2"></i>
                        Notes are saved to the database and visible to all team members.
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-ghost" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveCompanyNotes()">
                        <i class="fas fa-save me-2"></i>Save
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    return modal;
}

async function saveCompanyNotes() {
    const companyId = document.getElementById('notesCompanyId').value;
    const notes = document.getElementById('notesTextarea').value;
    const salesperson = document.getElementById('salespersonInput').value;
    
    try {
        const response = await fetch(`/api/company-notes/${companyId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                notes: notes,
                assigned_salesperson: salesperson
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('notesModal'));
            modal.hide();
            
            // Show success message
            showToast('Notes and salesperson saved successfully!', 'success');
            
            // Refresh data if needed
            if (typeof loadData === 'function') {
                loadData();
            }
        } else {
            alert('Error saving notes: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving notes:', error);
        alert('Error saving notes: ' + error.message);
    }
}

function showToast(message, type = 'info') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}


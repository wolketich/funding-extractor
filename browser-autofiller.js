// CSV Data Filler for Child Care Management System
(function() {
    // Track global state
    const state = {
      childrenByChick: {},
      totalMatches: 0
    };
    
    // Create UI elements for file upload and status
    createUI();
    
    // Main function to process the CSV file
    function processCSV(file) {
      const reader = new FileReader();
      
      reader.onload = function(e) {
        const csv = e.target.result;
        const data = parseCSV(csv);
        
        // Create a lookup object for easy access to child data by CHICK code
        state.childrenByChick = {};
        data.forEach(row => {
          state.childrenByChick[row['CHICK']] = row;
        });
        
        // Process the table rows
        processTableRows();
      };
      
      reader.onerror = function() {
        updateStatus('Error reading the file', 'error');
      };
      
      reader.readAsText(file);
    }
    
    // Parse CSV data
    function parseCSV(csv) {
      const lines = csv.split('\n');
      const headers = lines[0].split(',').map(h => h.trim());
      
      return lines.slice(1).filter(line => line.trim() !== '').map(line => {
        const values = line.split(',').map(v => v.trim());
        const obj = {};
        
        headers.forEach((header, i) => {
          obj[header] = values[i] || '';
        });
        
        return obj;
      });
    }
    
    // Process table rows and fill in data
    function processTableRows() {
      const table = document.querySelector("#main-body > div.container > form > div:nth-child(2) > table");
      
      if (!table) {
        updateStatus('Table not found on the page', 'error');
        return;
      }
      
      // Use tbody > tr selector since we know the structure now
      const rows = table.querySelectorAll('tbody > tr');
      
      if (rows.length === 0) {
        updateStatus('No rows found in the table', 'error');
        return;
      }
      
      updateStatus(`Found ${rows.length} rows to process`, 'info');
      state.totalMatches = 0;
      
      // Process rows sequentially
      processRowsSequentially(rows, 0);
    }
    
    // Process rows one by one
    function processRowsSequentially(rows, currentIndex) {
      // Remove any existing selection dialogs
      const oldDialogs = document.querySelectorAll('.csv-filler-modal');
      oldDialogs.forEach(dialog => document.body.removeChild(dialog));
      
      // Stop if we've processed all rows
      if (currentIndex >= rows.length) {
        updateStatus(`Successfully processed ${state.totalMatches} records`, 'success');
        return;
      }
      
      const row = rows[currentIndex];
      const chickCell = row.querySelector('td:nth-child(7)');
      
      if (!chickCell) {
        // Skip this row and move to the next
        processRowsSequentially(rows, currentIndex + 1);
        return;
      }
      
      const chickCode = chickCell.textContent.trim();
      
      // Check if this CHICK exists in our CSV data
      if (state.childrenByChick[chickCode]) {
        const childData = state.childrenByChick[chickCode];
        
        // Handle Weekly Total with multiple values
        const weeklyTotal = childData['Weekly Total'];
        
        if (weeklyTotal && weeklyTotal.includes('/')) {
          // Create a selection dialog for multiple weekly total values
          showWeeklyTotalSelector(currentIndex, chickCode, weeklyTotal.split('/'), childData, (selectedValue) => {
            fillRowData(currentIndex, childData, selectedValue);
            state.totalMatches++;
            // Continue with the next row after selection
            setTimeout(() => {
              processRowsSequentially(rows, currentIndex + 1);
            }, 300);
          });
          return;
        }
        
        // Fill in data for the row with a single value
        fillRowData(currentIndex, childData, weeklyTotal);
        state.totalMatches++;
        
        // Short delay to allow user to see the row being filled
        setTimeout(() => {
          processRowsSequentially(rows, currentIndex + 1);
        }, 100);
      } else {
        // No match for this row, move to the next
        processRowsSequentially(rows, currentIndex + 1);
      }
    }
    
    // Fill data for a specific row
    function fillRowData(rowIndex, childData, weeklyTotalValue) {
      try {
        // Get the row
        const table = document.querySelector("#main-body > div.container > form > div:nth-child(2) > table");
        const row = table.querySelector(`tbody > tr:nth-child(${rowIndex + 1})`);
        
        if (!row) {
          console.error(`Could not find row ${rowIndex + 1}`);
          return;
        }
        
        // Get input fields using exact selectors
        const startDateInput = row.querySelector(`input[name="ncs_rows[${rowIndex}][date_from]"]`);
        const weeklyTotalInput = row.querySelector(`input[name="ncs_rows[${rowIndex}][weekly_total]"]`);
        const hourRateInput = row.querySelector(`input[name="ncs_rows[${rowIndex}][hour_rate]"]`);
        
        if (startDateInput) {
          startDateInput.value = childData['Start date'] || '';
          startDateInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        if (weeklyTotalInput) {
          weeklyTotalInput.value = weeklyTotalValue || '';
          weeklyTotalInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        if (hourRateInput) {
          // Properly handle currency symbols by extracting only numbers and decimal point
          let hourRate = childData['Hour rate'] || '';
          hourRate = String(hourRate);
          hourRate = hourRate.replace(/[^0-9.]/g, '');
          hourRateInput.value = hourRate;
          hourRateInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        highlightRow(rowIndex, 'success');
        
        // Scroll row into view
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } catch (error) {
        console.error('Error filling row data:', error);
        highlightRow(rowIndex, 'error');
      }
    }
    
    // Show selector dialog for multiple Weekly Total values
    function showWeeklyTotalSelector(rowIndex, chickCode, values, childData, callback) {
      // Get row to position the modal near it
      const table = document.querySelector("#main-body > div.container > form > div:nth-child(2) > table");
      const row = table.querySelector(`tbody > tr:nth-child(${rowIndex + 1})`);
      
      if (row) {
        // Scroll row into view
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Add a small delay to ensure scrolling completes before showing the modal
        setTimeout(() => {
          createSelectionDialog(rowIndex, chickCode, values, childData, callback);
        }, 300);
      } else {
        createSelectionDialog(rowIndex, chickCode, values, childData, callback);
      }
      
      // Highlight the current row
      highlightRow(rowIndex, 'pending');
    }
    
    // Create the selection dialog
    function createSelectionDialog(rowIndex, chickCode, values, childData, callback) {
      // Get row position to place the modal nearby
      const table = document.querySelector("#main-body > div.container > form > div:nth-child(2) > table");
      const row = table.querySelector(`tbody > tr:nth-child(${rowIndex + 1})`);
      const rowRect = row.getBoundingClientRect();
      
      // Create a modal dialog
      const modal = document.createElement('div');
      modal.className = 'csv-filler-modal';
      
      // Position the modal to the right of the table, accounting for scroll position
      const modalLeft = Math.min(rowRect.right + 20, window.innerWidth - 320); // Avoid going off-screen
      const modalTop = window.scrollY + rowRect.top;
      
      modal.style.cssText = `
        position: absolute;
        top: ${modalTop}px;
        left: ${modalLeft}px;
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9999;
        width: 300px;
        font-family: Arial, sans-serif;
        animation: fadeIn 0.2s ease-out;
      `;
      
      // Create header bar with title and drag handle
      const headerBar = document.createElement('div');
      headerBar.style.cssText = 'display:flex;justify-content:space-between;align-items:center;cursor:move;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #eee;';
      
      const title = document.createElement('h3');
      title.textContent = `Weekly Total Options`;
      title.style.cssText = 'margin:0;font-size:16px;color:#444;';
      headerBar.appendChild(title);
      
      // Add handle visual
      const dragHandle = document.createElement('div');
      dragHandle.innerHTML = '⋮⋮';
      dragHandle.style.cssText = 'color:#999;font-size:16px;';
      headerBar.appendChild(dragHandle);
      
      modal.appendChild(headerBar);
      
      // Make the modal draggable
      makeElementDraggable(modal, headerBar);
      
      const childInfo = document.createElement('p');
      childInfo.textContent = `${childData['Child']} (${chickCode})`;
      childInfo.style.cssText = 'margin:0 0 12px 0;font-size:14px;color:#666;';
      modal.appendChild(childInfo);
      
      const description = document.createElement('p');
      description.textContent = 'Please select one of the following weekly total values:';
      description.style.cssText = 'margin:0 0 10px 0;font-size:14px;color:#333;';
      modal.appendChild(description);
      
      // Create options list
      const optionsList = document.createElement('div');
      optionsList.style.cssText = 'display:flex;flex-direction:column;gap:8px;margin:0 0 12px 0;';
      
      values.forEach((value, i) => {
        const option = document.createElement('div');
        option.style.cssText = `
          padding: 8px 12px;
          background-color: #f5f5f5;
          border: 1px solid #ddd;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          justify-content: space-between;
          align-items: center;
        `;
        
        const valueLabel = document.createElement('span');
        valueLabel.textContent = value;
        valueLabel.style.fontWeight = 'bold';
        option.appendChild(valueLabel);
        
        const selectBtn = document.createElement('button');
        selectBtn.textContent = 'Select';
        selectBtn.style.cssText = `
          background-color: #4CAF50;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 4px 8px;
          cursor: pointer;
          font-size: 12px;
        `;
        
        selectBtn.addEventListener('mouseover', () => {
          selectBtn.style.backgroundColor = '#45a049';
        });
        
        selectBtn.addEventListener('mouseout', () => {
          selectBtn.style.backgroundColor = '#4CAF50';
        });
        
        selectBtn.addEventListener('click', () => {
          document.body.removeChild(modal);
          callback(value);
        });
        
        option.appendChild(selectBtn);
        
        option.addEventListener('mouseover', () => {
          option.style.backgroundColor = '#e9e9e9';
        });
        
        option.addEventListener('mouseout', () => {
          option.style.backgroundColor = '#f5f5f5';
        });
        
        optionsList.appendChild(option);
      });
      
      modal.appendChild(optionsList);
      
      // Add skip button with fixed functionality
      const skipButton = document.createElement('button');
      skipButton.textContent = 'Skip This Row';
      skipButton.style.cssText = `
        width: 100%;
        padding: 8px;
        background-color: #f44336;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        transition: background-color 0.2s;
      `;
      
      skipButton.addEventListener('mouseover', () => {
        skipButton.style.backgroundColor = '#d32f2f';
      });
      
      skipButton.addEventListener('mouseout', () => {
        skipButton.style.backgroundColor = '#f44336';
      });
      
      skipButton.addEventListener('click', () => {
        document.body.removeChild(modal);
        
        // Get all rows again to continue processing from the next row
        const table = document.querySelector("#main-body > div.container > form > div:nth-child(2) > table");
        const rows = table.querySelectorAll('tbody > tr');
        
        // Continue with the next row
        setTimeout(() => {
          processRowsSequentially(rows, rowIndex + 1);
        }, 100);
      });
      
      modal.appendChild(skipButton);
      document.body.appendChild(modal);
    }
    
    // Make an element draggable
    function makeElementDraggable(element, handle) {
      let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
      
      handle.onmousedown = dragMouseDown;
      
      function dragMouseDown(e) {
        e = e || window.event;
        e.preventDefault();
        // Get the mouse cursor position at startup
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        // Call a function whenever the cursor moves
        document.onmousemove = elementDrag;
      }
      
      function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();
        // Calculate the new cursor position
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        // Set the element's new position
        element.style.top = (element.offsetTop - pos2) + "px";
        element.style.left = (element.offsetLeft - pos1) + "px";
      }
      
      function closeDragElement() {
        // Stop moving when mouse button is released
        document.onmouseup = null;
        document.onmousemove = null;
      }
    }
    
    // Highlight a row to indicate status
    function highlightRow(rowIndex, status) {
      const table = document.querySelector("#main-body > div.container > form > div:nth-child(2) > table");
      const row = table.querySelector(`tbody > tr:nth-child(${rowIndex + 1})`);
      
      if (!row) {
        console.error(`Could not find row ${rowIndex + 1} to highlight`);
        return;
      }
      
      // Remove existing highlight classes
      row.classList.remove('csv-filler-success', 'csv-filler-error', 'csv-filler-pending');
      
      // Add the appropriate class
      row.classList.add(`csv-filler-${status}`);
      
      // Add style definitions if they don't already exist
      addStylesIfNeeded();
    }
    
    // Create the UI elements for file upload
    function createUI() {
      // Check if the UI already exists
      if (document.getElementById('csv-filler-container')) {
        document.body.removeChild(document.getElementById('csv-filler-container'));
      }
      
      // Create the container
      const container = document.createElement('div');
      container.id = 'csv-filler-container';
      container.style.cssText = 'position:fixed;top:15px;right:15px;background-color:white;padding:15px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.2);z-index:9998;width:300px;font-family:Arial,sans-serif;';
      
      // Create a header bar with drag handle and minimize button
      const headerBar = document.createElement('div');
      headerBar.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;cursor:move;';
      container.appendChild(headerBar);
      
      // Make the container draggable
      makeElementDraggable(container, headerBar);
      
      const title = document.createElement('h3');
      title.textContent = 'CSV Data Filler';
      title.style.cssText = 'margin:0;font-size:16px;color:#444;';
      headerBar.appendChild(title);
      
      const controlButtons = document.createElement('div');
      controlButtons.style.cssText = 'display:flex;gap:5px;';
      headerBar.appendChild(controlButtons);
      
      // Minimize button
      const minimizeButton = document.createElement('button');
      minimizeButton.innerHTML = '−';
      minimizeButton.title = 'Minimize';
      minimizeButton.style.cssText = 'width:24px;height:24px;border:none;border-radius:50%;background-color:#f1f1f1;cursor:pointer;display:flex;align-items:center;justify-content:center;font-weight:bold;';
      minimizeButton.addEventListener('click', toggleMinimize);
      controlButtons.appendChild(minimizeButton);
      
      // Content area (can be minimized)
      const contentArea = document.createElement('div');
      contentArea.id = 'csv-filler-content';
      contentArea.style.cssText = 'transition:max-height 0.3s ease-out;overflow:hidden;max-height:500px;';
      container.appendChild(contentArea);
      
      const uploadLabel = document.createElement('label');
      uploadLabel.htmlFor = 'csv-file-input';
      uploadLabel.textContent = 'Upload CSV file:';
      uploadLabel.style.cssText = 'display:block;margin-bottom:8px;font-size:14px;color:#666;';
      contentArea.appendChild(uploadLabel);
      
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.id = 'csv-file-input';
      fileInput.accept = '.csv';
      fileInput.style.cssText = 'margin-bottom:12px;font-size:14px;width:100%;';
      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          processCSV(e.target.files[0]);
        }
      });
      contentArea.appendChild(fileInput);
      
      const statusDiv = document.createElement('div');
      statusDiv.id = 'csv-filler-status';
      statusDiv.style.cssText = 'margin-top:10px;padding:8px;background-color:#f0f0f0;border-radius:4px;font-size:14px;';
      statusDiv.textContent = 'Ready to process CSV file';
      contentArea.appendChild(statusDiv);
      
      document.body.appendChild(container);
      
      addStylesIfNeeded();
      
      // Function to toggle minimize state
      function toggleMinimize() {
        const content = document.getElementById('csv-filler-content');
        if (content.style.maxHeight !== '0px') {
          content.style.maxHeight = '0px';
          minimizeButton.innerHTML = '+';
          minimizeButton.title = 'Maximize';
          container.style.padding = '8px 15px';
        } else {
          content.style.maxHeight = '500px';
          minimizeButton.innerHTML = '−';
          minimizeButton.title = 'Minimize';
          container.style.padding = '15px';
        }
      }
    }
    
    // Add CSS styles for highlighting and UI elements
    function addStylesIfNeeded() {
      if (!document.getElementById('csv-filler-styles')) {
        const styleSheet = document.createElement('style');
        styleSheet.id = 'csv-filler-styles';
        styleSheet.textContent = `
          .csv-filler-success { 
            background-color: rgba(76, 175, 80, 0.15) !important; 
            transition: background-color 0.3s;
          }
          .csv-filler-error { 
            background-color: rgba(244, 67, 54, 0.15) !important; 
            transition: background-color 0.3s;
          }
          .csv-filler-pending { 
            background-color: rgba(255, 193, 7, 0.15) !important; 
            transition: background-color 0.3s;
          }
          #csv-filler-status {
            transition: background-color 0.3s, color 0.3s;
          }
          #csv-filler-status.success { 
            background-color: #e8f5e9; 
            color: #2e7d32; 
            border-left: 3px solid #4caf50;
          }
          #csv-filler-status.error { 
            background-color: #ffebee; 
            color: #c62828; 
            border-left: 3px solid #f44336;
          }
          #csv-filler-status.info { 
            background-color: #e3f2fd; 
            color: #1565c0; 
            border-left: 3px solid #2196f3;
          }
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
        `;
        document.head.appendChild(styleSheet);
      }
    }
    
    // Update the status display
    function updateStatus(message, type) {
      const statusDiv = document.getElementById('csv-filler-status');
      if (statusDiv) {
        statusDiv.textContent = message;
        statusDiv.className = type || '';
      }
    }
  })();
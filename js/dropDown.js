    const data = readJson()

    const sectionDropdown = document.getElementById("assay");
    const versionDropdown = document.getElementById("version");
    const output = document.getElementById("output");

    // Populate sections
    Object.keys(data).forEach(sec => {
      const opt = document.createElement("option");
      opt.value = sec;
      opt.textContent = sec;
      sectionDropdown.appendChild(opt);
    });

    // Update versions when section changes
    function updateVersions() {
      const section = sectionDropdown.value;
      versionDropdown.innerHTML = ""; // clear old options

      Object.keys(data[section]).forEach(ver => {
        const opt = document.createElement("option");
        opt.value = ver;
        opt.textContent = ver;
        versionDropdown.appendChild(opt);
      });

      // Show first version by default
      updateOutput();
    }

    // Show selected JSON
    function updateOutput() {
      const section = sectionDropdown.value;
      const version = versionDropdown.value;
      output.textContent = JSON.stringify(data[section][version], null, 2);
    }

    // Event listeners
    sectionDropdown.addEventListener("change", updateVersions);
    versionDropdown.addEventListener("change", updateOutput);

    // Initialize
    sectionDropdown.value = Object.keys(data)[0];
    updateVersions();

    const data = readJson()

    const sectionDropdown = document.getElementById("assay");
    const versionDropdown = document.getElementById("version");
    const reference = document.getElementById("reference");
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
      const sectionData = data[section];
      
      reference.textContent = sectionData["reference"] || "Not set";

      versionDropdown.innerHTML = ""; // clear old options

      // Show value
      // 
      Object.keys(sectionData)
        .filter(k => k !== "reference_for_species")
        .forEach(ver => {
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
      const jsonPretty = JSON.stringify(data[section][version], null, 2);
      output.textContent = jsonPretty.replace(/\[\s+([\s\S]*?)\s+\]/g, m =>m.replace(/\s+/g, '').replace(/,\]/, ']'))
    }

    // Event listeners
    sectionDropdown.addEventListener("change", updateVersions);
    versionDropdown.addEventListener("change", updateOutput);

    // Initialize
    sectionDropdown.value = Object.keys(data)[0];
    updateVersions();

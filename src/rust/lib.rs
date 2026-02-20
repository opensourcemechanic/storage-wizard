use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use std::time::SystemTime;
use walkdir::WalkDir;
use rayon::prelude::*;
use blake3::Hasher;
use std::fs::File;
use std::io::Read;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileInfo {
    pub path: String,
    pub size: u64,
    pub modified: u64,
    pub file_type: String,
    pub hash: Option<String>,
    pub is_temporary: bool,
    pub is_system_file: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectoryTree {
    pub path: String,
    pub files: Vec<FileInfo>,
    pub subdirectories: Vec<String>,
    pub total_size: u64,
    pub file_count: usize,
}

#[pyclass]
pub struct FastIndexer {
    #[pyo3(get)]
    base_path: String,
    #[pyo3(get)]
    indexed_files: HashMap<String, FileInfo>,
}

#[pymethods]
impl FastIndexer {
    #[new]
    fn new(base_path: String) -> Self {
        Self {
            base_path,
            indexed_files: HashMap::new(),
        }
    }

    fn scan_directory(&mut self, py: Python, include_hidden: bool) -> PyResult<PyObject> {
        let walker = WalkDir::new(&self.base_path)
            .follow_links(false)
            .max_depth(10);

        let entries: Vec<Result<walkdir::DirEntry, walkdir::Error>> = walker
            .into_iter()
            .filter_entry(|e| {
                if !include_hidden {
                    e.file_name()
                        .to_str()
                        .map(|s| !s.starts_with('.'))
                        .unwrap_or(true)
                } else {
                    true
                }
            })
            .collect();

        let files: Vec<FileInfo> = entries
            .into_par_iter()
            .filter_map(|entry| entry.ok())
            .filter(|e| e.file_type().is_file())
            .map(|entry| {
                let path = entry.path().to_string_lossy().to_string();
                let metadata = entry.metadata().ok()?;
                let size = metadata.len();
                let modified = metadata.modified()
                    .ok()
                    .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
                    .map(|d| d.as_secs())
                    .unwrap_or(0);
                
                let file_type = entry.path()
                    .extension()
                    .and_then(|ext| ext.to_str())
                    .unwrap_or("")
                    .to_lowercase();

                let is_temporary = is_temporary_file(&path);
                let is_system_file = is_system_file(&path);

                let file_info = FileInfo {
                    path,
                    size,
                    modified,
                    file_type,
                    hash: None,
                    is_temporary,
                    is_system_file,
                };

                self.indexed_files.insert(file_info.path.clone(), file_info.clone());
                Some(file_info)
            })
            .collect();

        let result = PyDict::new(py);
        result.set_item("files", files)?;
        result.set_item("total_files", self.indexed_files.len())?;
        Ok(result.into())
    }

    fn compute_hashes(&mut self, py: Python, batch_size: usize) -> PyResult<Vec<(String, String)>> {
        let files_to_hash: Vec<(String, String)> = self.indexed_files
            .iter_mut()
            .filter(|(_, info)| info.hash.is_none())
            .collect::<Vec<_>>()
            .chunks(batch_size)
            .collect::<Vec<_>>()
            .par_iter()
            .flat_map(|chunk| {
                chunk.iter().map(|(path, info)| {
                    let hash = compute_file_hash(path);
                    info.hash = hash.clone();
                    (path.clone(), hash.unwrap_or_default())
                }).collect::<Vec<_>>()
            })
            .collect();

        Ok(files_to_hash)
    }

    fn find_duplicates(&self) -> PyResult<Vec<Vec<String>>> {
        let mut hash_groups: HashMap<String, Vec<String>> = HashMap::new();
        
        for (path, info) in &self.indexed_files {
            if let Some(hash) = &info.hash {
                hash_groups.entry(hash.clone())
                    .or_insert_with(Vec::new)
                    .push(path.clone());
            }
        }

        let duplicates: Vec<Vec<String>> = hash_groups
            .into_values()
            .filter(|group| group.len() > 1)
            .collect();

        Ok(duplicates)
    }

    fn analyze_directory_trees(&self) -> PyResult<Vec<DirectoryTree>> {
        let mut trees: HashMap<String, DirectoryTree> = HashMap::new();
        
        for info in self.indexed_files.values() {
            let parent_path = Path::new(&info.path)
                .parent()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default();

            let tree = trees.entry(parent_path.clone()).or_insert_with(|| DirectoryTree {
                path: parent_path,
                files: Vec::new(),
                subdirectories: Vec::new(),
                total_size: 0,
                file_count: 0,
            });

            tree.files.push(info.clone());
            tree.total_size += info.size;
            tree.file_count += 1;
        }

        Ok(trees.into_values().collect())
    }

    fn suggest_cleanup(&self) -> PyResult<PyObject> {
        let py = Python::acquire_gil().python();
        let suggestions = PyDict::new(py);

        let temp_files: Vec<&FileInfo> = self.indexed_files
            .values()
            .filter(|info| info.is_temporary)
            .collect();
        suggestions.set_item("temporary_files", temp_files.len())?;

        let system_files: Vec<&FileInfo> = self.indexed_files
            .values()
            .filter(|info| info.is_system_file)
            .collect();
        suggestions.set_item("system_files", system_files.len())?;

        let large_files: Vec<&FileInfo> = self.indexed_files
            .values()
            .filter(|info| info.size > 100 * 1024 * 1024)
            .collect();
        suggestions.set_item("large_files", large_files.len())?;

        Ok(suggestions.into())
    }
}

fn is_temporary_file(path: &str) -> bool {
    let filename = Path::new(path)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("");
    
    let temp_patterns = [
        ".tmp", ".temp", "~$", ".swp", ".bak", ".old",
        "Thumbs.db", "Desktop.ini", ".DS_Store", "._",
    ];

    temp_patterns.iter().any(|pattern| filename.contains(pattern))
}

fn is_system_file(path: &str) -> bool {
    let path_lower = path.to_lowercase();
    let system_indicators = [
        "system volume information",
        "$recycle.bin",
        "recycler",
        "pagefile.sys",
        "hiberfil.sys",
        "swapfile.sys",
    ];

    system_indicators.iter().any(|indicator| path_lower.contains(indicator))
}

fn compute_file_hash(path: &str) -> Option<String> {
    let mut file = File::open(path).ok()?;
    let mut hasher = Hasher::new();
    let mut buffer = [0; 8192];

    loop {
        let bytes_read = file.read(&mut buffer).ok()?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }

    Some(hasher.finalize().to_hex().to_string())
}

#[pymodule]
fn storage_wizard_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<FastIndexer>()?;
    Ok(())
}

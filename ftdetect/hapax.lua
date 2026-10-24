-- Hapax instrument definitions are .txt files; the first non-comment line decides.
-- It must be a whole directive (TRACKNAME takes any name, the rest one value) or a section header.
local starts = {
  VERSION = true, TRACKNAME = true, TYPE = true, OUTPORT = true,
  OUTCHAN = true, INPORT = true, INCHAN = true, MAXRATE = true,
}

local function hapax(line)
  if line:match("^%s*%[/?[%a_]+%]%s*$") then
    return true
  end
  local key, value = line:match("^%s*(%a+)%s+(.-)%s*$")
  key = key and key:upper()
  return key ~= nil and starts[key] ~= nil and (key == "TRACKNAME" or not value:find("%s"))
end

local function detect(_, bufnr)
  for _, line in ipairs(vim.api.nvim_buf_get_lines(bufnr, 0, 50, false)) do
    line = line:gsub("#.*", "")
    if line:find("%S") then
      return hapax(line) and "hapax" or "text"
    end
  end
  return "text"
end

vim.filetype.add({ extension = { txt = detect } })

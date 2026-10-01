-- Hapax instrument definitions are .txt files; the first non-comment line decides.
local starts = {
  VERSION = true, TRACKNAME = true, TYPE = true, OUTPORT = true,
  OUTCHAN = true, INPORT = true, INCHAN = true, MAXRATE = true,
}

vim.filetype.add({
  extension = {
    txt = function(_, bufnr)
      for _, line in ipairs(vim.api.nvim_buf_get_lines(bufnr, 0, 50, false)) do
        local word = line:gsub("#.*", ""):match("^%s*(%S+)")
        if word then
          return (word:sub(1, 1) == "[" or starts[word:upper()]) and "hapax" or "text"
        end
      end
      return "text"
    end,
  },
})

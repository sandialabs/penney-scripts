" vimrc configuration file with a whole bunch of added stuff to browse note
" files and function as a fully-fledged embedded IDE.

set encoding=utf-8
scriptencoding utf-8
"Vimrc customization file

" Add the $HOME/.vim folder on Windows machines
" See :help feature-list
if has('win32') || has('win64') || has('win32unix')
  set runtimepath^=$HOME/.vim
endif

"General keymapping
let mapleader = ';'  " Set the <leader> key to semicolon (;)

" General view/edit settings
set hlsearch    " Turn on search highlighting
" The below is all to set tabs to 2 characters (except for Python files)
" and replace them with spaces
set tabstop=2
set shiftwidth=2
autocmd FileType python set tabstop=4
autocmd FileType python set shiftwidth=4
set softtabstop=0
set expandtab
set smarttab

" -------------- Vundle Plugin Manager Settings --------------
" Install Vundle with:
" git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim
"
" Once Vundle is installed, run :PluginInstall to install the following from
" github.

if finddir($HOME . "/.vim/bundle/Vundle.vim") != ""
  filetype off
  set rtp+=$HOME/.vim/bundle/Vundle.vim
  call vundle#begin()
  Plugin 'VundleVim/Vundle.vim'
  Plugin 'preservim/nerdtree'
  Plugin 'jistr/vim-nerdtree-tabs'
  " Plugin 'xolox/vim-misc'
  " Plugin 'xolox/vim-easytags'
  Plugin 'jsfaint/gen_tags.vim'
  Plugin 'majutsushi/tagbar'
  Plugin 'ctrlpvim/ctrlp.vim'
  call vundle#end()
  filetype plugin indent on
endif

let _bundleDir = $HOME . "/.vim/bundle/"
function! BundleExists(name)
  if finddir(g:_bundleDir . a:name) != ""
    return 1
  else
    return 0
  endif
endfunction

let _pnerdtree = 0
if finddir($HOME . "/.vim/bundle/nerdtree") != ""
  let g:_pnerdtree = 1
endif

let _pnerdtreetabs = 0
if finddir($HOME . "/.vim/bundle/vim-nerdtree-tabs") != ""
  let g:_pnerdtreetabs = 1
endif

let _pvimmisc = 0
if BundleExists("vim-misc")
  let _pvimmisc = 1
endif

if has('win32') || has('win64') || has('win32unix')
  let ctags_cmd = 'C:/toolchains/ctags/ctags.exe'
else
  let ctags_cmd = '/usr/bin/ctags'
endif

let _pgentags = 0
if BundleExists("gen_tags.vim")
  let _pgentags = 1
  " Disable 'gtags' support
  let g:gen_tags#ctags_bin = ctags_cmd
  let g:loaded_gentags#gtags = 1
  " Use the template below to customize options to ctags
  " let g:gen_tags#ctags_opts = ['opt1', 'opt2', ...]
endif

let _pvimeasytags = 0
if BundleExists("vim-easytags")
  let _pvimeasytags = 1
  set tags=./tags;,~/.vimtags
  let g:easytags_events = ['BufReadPost', 'BufWritePost']
  let g:easytags_async = 1
  let g:easytags_dynamic_files = 2
  let g:easytags_resolve_links = 1
  let g:easytags_suppress_ctags_warning = 1
  "let g:easytags_opts += ['-R']
  let g:easytags_cmd = ctags_cmd
endif

let _ptagbar = 0
if BundleExists("tagbar")
  let _ptagbar = 1
  let g:tagbar_ctags_bin = ctags_cmd
endif

" ------------------------------------------------------------

" --------------------- Look and Feel ------------------------
syntax on
let g:solarized_termcolors=256
" colorscheme solarized

" Enable the mouse
set mouse=a

" ------------------------------------------------------------

" -------------------- Custom Functions ----------------------
"The below is to make whitespace visible using the prescribed characters
"Using the argument 'space' requires version>7.4.710
if has("patch-7.4.710")
    set listchars=space:·,eol:¬,tab:>·
else
    set listchars=eol:¬,tab:>·
endif
set list
"This function inserts an underline immediately following the current line
"copying the same leading whitespace to make it look right
function! Underline()
  let currentline = getline('.')
  let nspaces = match(currentline, '[^ \t]')                "Get the first non-whitespace character index
  let nchars = strlen(currentline) - nspaces                "Calculate the number of non-whitespace chars
  let uline = repeat(' ', nspaces) . repeat('-', nchars)    "Build the underline string
  call append(line("."), uline)                             "Append the underline
  "execute "normal! o"                                       "Jump to the next line and re-enter input mode
endfunction

"This function searches for the next line (earlier in the file if 'up') which
"has non-whitespace at or before the current cursor column and jumps to that line.
"It's most useful for navigating text files formatted by indentation (i.e. Python
"scripts).
function! NextAtIndent(up)
  "echom "NextAtIndent()"
  let currline = line('.')          "Get the current line number
  let lastline = line('$')          "Get the number of the last line in the file
  let currcol = col('.')            "Get the current column number
  "echom "currline = " . currline . "\tcurrcol = " . currcol . "\tlastline = " . lastline
  let newcol = currcol              "Default values in case our search turns up empty
  let newline = currline            "for both line and column
  if a:up                           "If we are counting down (prior lines)
    if currline == 0                "If called on line 0, just return
      return 1
    endif
    let linerange = range(currline - 1, 0, -1)  "Otherwise, set the line range to decrement
  else                              "If we are counting up (subsequent lines)
    if currline == lastline         "If called at the bottom line, just return
      return 1
    endif
    let linerange = range(currline + 1, lastline) "Otherwise, set the line range to increment
  endif
  for n in linerange                "Loop through the rest of the lines in the file
    "echom "line num: " . n
    let linecontents = getline(n)   "Get the contents of the next line
    if linecontents[0:currcol] =~ '\S'   "If the line up to the current column is not all whitespace
      "echom "Line hit: " . linecontents[0:currcol]
      let newline = n               "Save the destination line
      let newcol = match(linecontents, '\S') + 1 "Get the index of the first non-whitespace char in the line
      break
    endif
  endfor
  "echom "newline = " . newline . "\tnewcol = " . newcol
  "call cursor(newline, newcol)           "Move the cursor to the new line/column
  call setpos('.', [0, newline, newcol, 0])
endfunction

"This function searches for the next line (earlier in the file if 'up') which
"contains a C function definition and jumps to it if found.
function! NextCDef(up)
  let currline = line('.')          "Get the current line number
  let lastline = line('$')          "Get the number of the last line in the file
  let newline = currline            "for both line and column
  if a:up                           "If we are counting down (prior lines)
    if currline == 0                "If called on line 0, just return
      return 1
    endif
    let linerange = range(currline - 1, 0, -1)  "Otherwise, set the line range to decrement
  else                              "If we are counting up (subsequent lines)
    if currline == lastline         "If called at the bottom line, just return
      return 1
    endif
    let linerange = range(currline + 1, lastline) "Otherwise, set the line range to increment
  endif
  for n in linerange                "Loop through the rest of the lines in the file
    let linecontents = getline(n)   "Get the contents of the next line
    if linecontents =~ '\v^\w+\s+\w+\('  "If the line matches a C function signature
      let newline = n               "Save the destination line
      break
    endif
  endfor
  call setpos('.', [0, newline, 0, 0])
endfunction

" ------------------------------------------------------------

" ---------------------- Key Mappings ------------------------
  " Jump to next/previous indent with J/K
nmap <silent> J :call NextAtIndent(0)<CR>
nmap <silent> K :call NextAtIndent(1)<CR>
  " If editing a C file, instead jump to next/previous function def'n
autocmd FileType c nnoremap <silent> <buffer> J :call NextCDef(0)<CR>
autocmd FileType c nnoremap <silent> <buffer> K :call NextCDef(1)<CR>

  " Turn off syntax highlighting with ;h
nnoremap <leader>h :nohls<CR>

  "Note that we can toggle whitespace visibility with F5
nmap <F5> :set list!<CR>

  "This is a handy way to convert the current word to all UPPERCASE (Ctrl+K)
nmap <c-k> viwU
  "And a complement to convert to all lowercase (Ctrl+L)
nmap <c-l> viwu

  " Underline the current line (in a newline below)
nmap <F6> :call Underline()<CR>

  " Just make :W do the same as :w (so annoying!)
command! W :w

"nmap <c-r> :call system(ctags_cmd . "-R .")<CR>

  " Filter the current buffer through xxd to view it as in a hex editor
command! Hexify %!xxd

  " Create a function comment in C. Call on the line of the function
  " definition and make sure there's no comment line directly above.
command! J yyko/*<cr><cr>/<esc>kkp0i * <esc>A<bs><bs>;<esc>jA    

  " = = = = = =  Some plugin-specific key mappings = = = = = = 

if _pnerdtree
  " Display the NERDTree panel (if installed) with <leader>t
  nmap <silent> <leader>t :NERDTreeTabsToggle<CR>
  " This allows vim to close if the only thing open is NERDTree
  autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTree") && b:NERDTree.isTabTree()) | q | endif
endif

if _pgentags
  "nmap <c-r> :GenCtags
endif

if _ptagbar
  " Display the tagbar (if installed) with <leader>b
  nmap <silent> <leader>b :TagbarToggle<CR>
endif

  " Embedded-specific tools
nmap <leader>m :call system("make")<CR>
nmap <leader>c :call system("make clean")<CR>
nmap <leader>f :call system("make openocd_flash")<CR>
" ------------------------------------------------------------


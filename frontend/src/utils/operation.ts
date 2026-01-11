export function applyOperation(content: string, operation: {
  type: 'insert' | 'delete' | 'replace'
  from_pos: number
  to_pos: number
  content?: string
}): string {
  const { type, from_pos, to_pos, content: opContent } = operation

  if (type === 'insert') {
    if (from_pos !== to_pos) {
      throw new Error('insert 操作的 from_pos 和 to_pos 必须相等')
    }
    if (from_pos > content.length) {
      throw new Error(`插入位置 ${from_pos} 超出文档长度 ${content.length}`)
    }
    if (!opContent) {
      throw new Error('insert 操作必须提供 content')
    }
    return content.slice(0, from_pos) + opContent + content.slice(from_pos)
  }

  if (type === 'delete') {
    if (from_pos >= to_pos) {
      throw new Error('delete 操作的 from_pos 必须小于 to_pos')
    }
    if (to_pos > content.length) {
      throw new Error(`删除位置 ${to_pos} 超出文档长度 ${content.length}`)
    }
    return content.slice(0, from_pos) + content.slice(to_pos)
  }

  if (type === 'replace') {
    if (from_pos >= to_pos) {
      throw new Error('replace 操作的 from_pos 必须小于 to_pos')
    }
    if (to_pos > content.length) {
      throw new Error(`替换位置 ${to_pos} 超出文档长度 ${content.length}`)
    }
    if (!opContent) {
      throw new Error('replace 操作必须提供 content')
    }
    return content.slice(0, from_pos) + opContent + content.slice(to_pos)
  }

  throw new Error(`不支持的操作类型: ${type}`)
}


export function adjustCursorPosition(
  cursorPos: number,
  operation: {
    type: 'insert' | 'delete' | 'replace' | 'format'
    from_pos: number
    to_pos: number
    content?: string
  }
): number {
  const { type, from_pos, to_pos, content: opContent } = operation
  
  if (type === 'format') {
    return cursorPos
  }
  
  if (type === 'insert') {
    if (from_pos > cursorPos) {
      return cursorPos
    }
    const insertLength = opContent ? opContent.length : 0
    return cursorPos + insertLength
  }
  
  if (type === 'delete') {
    if (from_pos >= cursorPos) {
      return cursorPos
    }
    if (to_pos <= cursorPos) {
      const deleteLength = to_pos - from_pos
      return cursorPos - deleteLength
    }
    if (from_pos < cursorPos && cursorPos < to_pos) {
      return from_pos
    }
    return cursorPos
  }
  
  if (type === 'replace') {
    const oldLength = to_pos - from_pos
    const newLength = opContent ? opContent.length : 0
    const diff = newLength - oldLength
    
    if (from_pos >= cursorPos) {
      return cursorPos
    }
    
    if (to_pos <= cursorPos) {
      return cursorPos + diff
    }
    
    if (from_pos < cursorPos && cursorPos < to_pos) {
      return from_pos + newLength
    }
    
    return cursorPos
  }
  
  return cursorPos
}


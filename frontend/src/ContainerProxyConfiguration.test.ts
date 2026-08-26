// @ts-expect-error Vitest provides Node at test runtime; the browser bundle does not use this module.
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('container API proxy configuration', () => {
  it('gives every Dockerized frontend the backend service target by default', () => {
    // @ts-expect-error Test runtime is Node; production browser code never imports this file.
    const dockerfile = readFileSync(`${process.cwd()}/Dockerfile`, 'utf8')
    expect(dockerfile).toContain('ENV VITE_API_PROXY_TARGET=http://backend:8000')
  })
})
